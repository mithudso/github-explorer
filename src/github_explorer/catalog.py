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
    result = subprocess.run(
        [executable(), *args],
        cwd=cwd,
        env={**os.environ, "GH_PAGER": "cat", "PAGER": "cat", "NO_COLOR": "1"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "gh help failed")
    return result.stdout


def load_catalog(cwd: Path) -> list[Command]:
    return parse_catalog(help_text(["help", "reference"], cwd), help_text(["--help"], cwd))
