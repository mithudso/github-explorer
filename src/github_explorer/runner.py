"""Shell-free command execution with cancellation and bounded captured output."""

from __future__ import annotations

import base64
import codecs
import json
import math
import os
import selectors
import shlex
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlsplit

from .catalog import executable

OUTPUT_LIMIT = 2_000_000


@dataclass(frozen=True)
class Invocation:
    argv: tuple[str, ...]
    cwd: Path
    repo: str = ""
    program: str = "gh"

    @property
    def preview(self) -> str:
        if self.program == "git":
            return (
                f"Directory: {self.cwd}\nGit uses this checkout's configured remote/upstream.\n"
                "The GitHub repository override does not apply.\n"
                f"{shlex.join(self.argv)}"
            )
        return f"Directory: {self.cwd}\nGH_REPO: {self.repo or '(infer from directory)'}\n{shlex.join(self.argv)}"

    def environment(self, interactive=False) -> dict[str, str]:
        env = dict(os.environ)
        env.pop("GH_REPO", None)
        if self.repo and self.program == "gh":
            env["GH_REPO"] = self.repo
        if not interactive:
            env.update(GH_PROMPT_DISABLED="1", GH_PAGER="cat", PAGER="cat", NO_COLOR="1")
            env.pop("GH_FORCE_TTY", None)
            if self.program == "git":
                env.update(GIT_TERMINAL_PROMPT="0", GIT_PAGER="cat")
        return env


def git_executable() -> str:
    path = shutil.which("git")
    if not path:
        raise ValueError("Git is not installed or is not on PATH")
    return path


def prepare(command: str, cwd: str | Path, repo: str = "") -> Invocation:
    words = shlex.split(command)
    program = "git" if words and words[0] == "git" else "gh"
    if words and words[0] in {"gh", "git"}:
        words.pop(0)
    if not words:
        raise ValueError("Select or enter a gh or git command")
    # These would not be shell operators with shell=False, but rejecting them
    # prevents an accidental 'gh command && ...' from becoming gh arguments.
    if any(word in {";", "&&", "||", "|", ">", ">>", "<"} for word in words):
        raise ValueError("Enter one command; shell operators are not supported")
    directory = Path(cwd).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("Choose an existing working directory")
    repo = repo.strip()
    if program == "gh" and repo and not (re_repo(repo)):
        raise ValueError("Repository must be OWNER/REPO or HOST/OWNER/REPO")
    binary = git_executable() if program == "git" else executable()
    return Invocation((binary, *words), directory, repo if program == "gh" else "", program)


def re_repo(value: str) -> bool:
    import re

    return bool(re.fullmatch(r"(?:[\w.-]+(?::\d+)?/)?[\w.-]+/[\w.-]+", value))


@dataclass(frozen=True)
class Result:
    returncode: int
    output: str
    cancelled: bool = False
    timed_out: bool = False
    truncated: bool = False


class CommandRunner:
    def __init__(self):
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    @staticmethod
    def stop(process):
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                # macOS may reject a second signal after the group has exited.
                # Fall back to the owned child if it is still alive.
                if process.poll() is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
        elif process.poll() is None:
            process.kill()

    def run(
        self,
        invocation: Invocation,
        on_output: Callable[[str], None],
        timeout: float = 300,
    ) -> Result:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be finite and positive")
        if self.cancelled.is_set():
            return Result(-1, "", cancelled=True)
        process = subprocess.Popen(
            invocation.argv,
            cwd=invocation.cwd,
            env=invocation.environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=os.name == "posix",
        )
        output = ""
        timed_out = truncated = False
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        started = time.monotonic()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    timed_out = time.monotonic() - started >= timeout
                    if self.cancelled.is_set() or timed_out:
                        self.stop(process)
                        break
                    for key, _ in selector.select(0.1):
                        chunk = os.read(key.fd, 8192)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        text = decoder.decode(chunk, final=not chunk)
                        room = max(0, OUTPUT_LIMIT - len(output))
                        if room and text:
                            output += text[:room]
                            on_output(text[:room])
                        truncated |= len(text) > room
                while process.poll() is None:
                    timed_out = time.monotonic() - started >= timeout
                    if self.cancelled.is_set() or timed_out:
                        self.stop(process)
                        break
                    self.cancelled.wait(0.05)
            return Result(process.wait(), output, self.cancelled.is_set(), timed_out, truncated)
        finally:
            self.stop(process)
            process.wait()
            process.stdout.close()


def run_interactive(invocation: Invocation) -> int:
    """Call while the host app is suspended, retaining normal terminal prompts."""
    try:
        return subprocess.call(
            invocation.argv, cwd=invocation.cwd, env=invocation.environment(True)
        )
    except KeyboardInterrupt:
        return 130


@dataclass(frozen=True)
class Repository:
    context: Invocation
    name: str
    host: str
    branch: str
    settings: dict

    @property
    def target(self) -> str:
        return f"{self.host}/{self.name}"


def read_json(invocation: Invocation, executor: CommandRunner) -> dict:
    """Read bounded JSON through the same cancellable subprocess implementation."""
    result = executor.run(invocation, lambda text: None, timeout=30)
    if result.cancelled:
        raise ValueError("Repository read cancelled")
    if result.timed_out:
        raise ValueError("Repository read timed out after 30 seconds")
    if result.returncode:
        raise ValueError(result.output.strip() or f"GitHub exited with {result.returncode}")
    if result.truncated:
        raise ValueError("Repository response exceeds the capture limit; narrow the request")
    data = json.loads(result.output)
    if not isinstance(data, dict):
        raise ValueError("Expected a GitHub JSON object")
    return data


def api_read(repository: Repository, endpoint: str, executor: CommandRunner) -> dict:
    context = repository.context
    return read_json(Invocation(
        (context.argv[0], "api", "--method", "GET", "--hostname", repository.host,
         f"repos/{repository.name}/{endpoint}".rstrip("/")),
        context.cwd, repository.target,
    ), executor)


def repository_info(context: Invocation, executor: CommandRunner) -> Repository:
    identity = read_json(Invocation(
        (context.argv[0], "repo", "view", "--json", "nameWithOwner,url"),
        context.cwd, context.repo,
    ), executor)
    name = identity.get("nameWithOwner", "")
    url = urlsplit(identity.get("url", ""))
    if not re_repo(name) or name.count("/") != 1 or url.scheme != "https" or not url.hostname:
        raise ValueError("GitHub returned an invalid repository identity")
    if url.username or url.password:
        raise ValueError("GitHub returned an invalid repository URL")
    repository = Repository(context, name, url.netloc, "", {})
    settings = api_read(repository, "", executor)
    return Repository(context, name, url.netloc, settings.get("default_branch") or "", settings)


def repository_files(repository: Repository, executor: CommandRunner) -> list[dict]:
    """Walk individual Git trees so recursive API truncation never hides files."""
    if not repository.branch:
        return []
    pending = [("", repository.branch)]
    files = []
    while pending:
        prefix, ref = pending.pop()
        try:
            data = api_read(repository, f"git/trees/{quote(ref, safe='')}", executor)
        except ValueError as exc:
            if not prefix and "Git Repository is empty" in str(exc):
                return []
            raise
        if data.get("truncated"):
            raise ValueError("GitHub truncated a directory listing; the file list is incomplete")
        for entry in data.get("tree", []):
            path = prefix + entry["path"]
            if entry["type"] == "tree":
                pending.append((path + "/", entry["sha"]))
            else:
                files.append({**entry, "path": path})
    return sorted(files, key=lambda entry: entry["path"])


def repository_file_text(repository: Repository, entry: dict, executor: CommandRunner) -> str:
    if entry["type"] == "commit":
        return f"Submodule at commit {entry['sha']}"
    if entry.get("size", 0) > 500_000:
        return "Preview unavailable: file exceeds 500 KB."
    data = api_read(repository, f"git/blobs/{quote(entry['sha'], safe='')}", executor)
    if data.get("encoding") != "base64":
        raise ValueError("GitHub returned an unsupported file encoding")
    content = base64.b64decode(data.get("content", ""))
    if len(content) > 500_000:
        return "Preview unavailable: file exceeds 500 KB."
    if b"\0" in content:
        return "Binary file; text preview unavailable."
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return "Non-UTF-8 file; text preview unavailable."
