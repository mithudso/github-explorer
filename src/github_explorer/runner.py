"""Shell-free command execution with cancellation and bounded captured output."""

from __future__ import annotations

import codecs
import os
import selectors
import shlex
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .catalog import executable

OUTPUT_LIMIT = 2_000_000


@dataclass(frozen=True)
class Invocation:
    argv: tuple[str, ...]
    cwd: Path
    repo: str = ""

    @property
    def preview(self) -> str:
        return f"Directory: {self.cwd}\nGH_REPO: {self.repo or '(infer from directory)'}\n{shlex.join(self.argv)}"

    def environment(self, interactive=False) -> dict[str, str]:
        env = dict(os.environ)
        env.pop("GH_REPO", None)
        if self.repo:
            env["GH_REPO"] = self.repo
        if not interactive:
            env.update(GH_PROMPT_DISABLED="1", GH_PAGER="cat", PAGER="cat", NO_COLOR="1")
            env.pop("GH_FORCE_TTY", None)
        return env


def prepare(command: str, cwd: str | Path, repo: str = "") -> Invocation:
    words = shlex.split(command)
    if words and words[0] == "gh":
        words.pop(0)
    if not words:
        raise ValueError("Select or enter a gh command")
    # These would not be shell operators with shell=False, but rejecting them
    # prevents an accidental 'gh command && ...' from becoming gh arguments.
    if any(word in {";", "&&", "||", "|", ">", ">>", "<"} for word in words):
        raise ValueError("Enter one gh command; shell operators are not supported")
    directory = Path(cwd).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("Choose an existing working directory")
    repo = repo.strip()
    if repo and not (re_repo(repo)):
        raise ValueError("Repository must be OWNER/REPO or HOST/OWNER/REPO")
    return Invocation((executable(), *words), directory, repo)


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
        if timeout <= 0:
            raise ValueError("Timeout must be positive")
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
                            continue
                        text = decoder.decode(chunk)
                        room = max(0, OUTPUT_LIMIT - len(output))
                        if room:
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
