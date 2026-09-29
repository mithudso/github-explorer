"""Read the installed CLI's built-in reference; do not run aliases or extensions."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class Flag:
    name: str
    value_type: str = ""
    description: str = ""


@dataclass(frozen=True)
class Command:
    path: tuple[str, ...]
    summary: str
    help: str
    flags: tuple[Flag, ...] = ()
    external: bool = False

    @property
    def name(self) -> str:
        return " ".join(self.path)


def flags_from_help(text: str) -> tuple[Flag, ...]:
    flags = {}
    for line in text.splitlines():
        match = re.match(r"^\s+(?:-\w,\s+)?(--[\w-]+)(?:[ =]([^\s].*?))?\s{2,}(.*)$", line)
        if match:
            name, value, description = match.groups()
            flags[name] = Flag(name, value or "", description)
    return tuple(flags.values())


def parse_catalog(reference: str, root_help: str = "") -> list[Command]:
    headings = list(re.finditer(r"^#{2,} gh (.+)$", reference, re.M))
    commands = {}
    for index, heading in enumerate(headings):
        words = []
        for word in heading[1].split():
            if not re.fullmatch(r"[a-z][a-z0-9-]*", word):
                break
            words.append(word)
        if not words:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(reference)
        section = reference[heading.start() : end].strip()
        body = section.splitlines()[1:]
        summary = next((line.strip() for line in body if line.strip()), "")
        path = tuple(words)
        commands[path] = Command(path, summary, section, flags_from_help(section))
    section = ""
    for line in root_help.splitlines():
        if line and not line[0].isspace():
            section = line
        match = re.match(r"^  ([\w-]+):\s+(.+)$", line)
        if match and "COMMANDS" in section:
            path = (match[1],)
            if path in commands and section in {"ALIAS COMMANDS", "EXTENSION COMMANDS"}:
                commands[path] = replace(commands[path], external=True)
            elif path not in commands:
                commands[path] = Command(
                    path,
                    match[2],
                    f"gh {match[1]}\n\n{match[2]}\n\nUse Fetch help to request this command's help."
                    " Aliases and extensions may invoke external programs.",
                    external=True,
                )
    return sorted(commands.values(), key=lambda c: c.path)


def executable() -> str:
    path = shutil.which("gh")
    if not path:
        raise ValueError("GitHub CLI (gh) is not installed or is not on PATH")
    return path


def help_text(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            [executable(), *args],
            cwd=cwd,
            env={**os.environ, "GH_PAGER": "cat", "PAGER": "cat", "NO_COLOR": "1"},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("GitHub CLI help timed out after 30 seconds") from exc
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "gh help failed")
    return result.stdout


def load_catalog(cwd: Path) -> list[Command]:
    return parse_catalog(help_text(["help", "reference"], cwd), help_text(["--help"], cwd))


def repository_settings(cwd: Path) -> tuple[Flag, ...]:
    """Discover every setting offered by this installation's built-in repo editor."""
    return tuple(
        flag for flag in flags_from_help(help_text(["repo", "edit", "--help"], cwd))
        if flag.name != "--help"
    )


def setting_value(flag: Flag, settings: dict):
    """Map known REST properties; absence means unknown, never false."""
    names = {
        "--description": "description", "--homepage": "homepage",
        "--default-branch": "default_branch", "--visibility": "visibility",
        "--template": "is_template", "--allow-forking": "allow_forking",
        "--allow-update-branch": "allow_update_branch",
        "--delete-branch-on-merge": "delete_branch_on_merge",
        "--enable-auto-merge": "allow_auto_merge", "--enable-discussions": "has_discussions",
        "--enable-issues": "has_issues", "--enable-projects": "has_projects",
        "--enable-wiki": "has_wiki", "--enable-merge-commit": "allow_merge_commit",
        "--enable-rebase-merge": "allow_rebase_merge",
        "--enable-squash-merge": "allow_squash_merge",
    }
    if flag.name in names:
        key = names[flag.name]
        if key in settings and flag.name in {"--description", "--homepage"}:
            return settings[key] or ""
        return settings[key] if settings.get(key) is not None else None
    security = {
        "--enable-advanced-security": "advanced_security",
        "--enable-secret-scanning": "secret_scanning",
        "--enable-secret-scanning-push-protection": "secret_scanning_push_protection",
    }
    if flag.name in security:
        state = (settings.get("security_and_analysis") or {}).get(security[flag.name], {})
        if state.get("status") in {"enabled", "disabled"}:
            return state["status"] == "enabled"
    if flag.name == "--squash-merge-commit-message":
        modes = {
            ("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"): "default",
            ("PR_TITLE", "BLANK"): "pr-title",
            ("PR_TITLE", "COMMIT_MESSAGES"): "pr-title-commits",
            ("PR_TITLE", "PR_BODY"): "pr-title-description",
        }
        return modes.get((settings.get("squash_merge_commit_title"),
                          settings.get("squash_merge_commit_message")))
    return None


def settings_arguments(flags: tuple[Flag, ...], changes: dict[str, str]) -> list[str]:
    """Only selected settings enter argv; empty strings can clear text properties."""
    known = {flag.name: flag for flag in flags}
    if not changes:
        raise ValueError("Select at least one setting to change")
    if set(changes) - known.keys():
        raise ValueError("Unknown repository setting")
    if "--visibility" in changes and changes.get("--accept-visibility-change-consequences") != "true":
        raise ValueError("Select and enable --accept-visibility-change-consequences first")
    if "--squash-merge-commit-message" in changes and changes.get("--enable-squash-merge") != "true":
        raise ValueError("Select and enable --enable-squash-merge to change its message format")
    args = []
    for name, value in changes.items():
        if not known[name].value_type and value not in {"true", "false"}:
            raise ValueError(f"Choose true or false for {name}")
        if not value and name not in {"--description", "--homepage"}:
            raise ValueError(f"Enter a value for {name}")
        args.append(f"{name}={value}")
    return args
