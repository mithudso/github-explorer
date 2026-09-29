#!/usr/bin/env python3
"""Archive old workflow sections, preserving headers and recent continuation context."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def plan_rotation(root: Path, threshold: int, keep: int) -> list[tuple[Path, str, str]]:
    """Read both logs before any write; refuse live editor markers and unsafe paths."""
    if threshold < 1 or keep < 1:
        raise ValueError("threshold and keep must be positive")
    plans = []
    for name in ("prompts.md", "memory.md"):
        path = root / name
        if path.is_symlink():
            raise ValueError(f"Refusing symlink: {name}")
        markers = [*root.glob(f".{name}.sw*"), root / f"{name}~", root / f".#{name}"]
        if any(marker.exists() for marker in markers):
            raise ValueError(f"Editor marker found for {name}; close the editor before rotation")
        if not path.exists() or path.stat().st_size <= threshold:
            continue
        content = path.read_text()
        # Only top-level workflow sections. Ignore Markdown headings in code fences.
        starts, offset, fence = [], 0, None
        for line in content.splitlines(keepends=True):
            stripped = line.lstrip()
            marker = re.match(r"(`{3,}|~{3,})", stripped)
            if marker:
                token = marker[1]
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
            elif fence is None and re.match(r"^## (?:Prompt v|v\d|\d{4}-\d{2}-\d{2})", line):
                starts.append(offset)
            offset += len(line)
        if len(starts) <= keep:
            continue
        cut = starts[-keep]
        plans.append((path, content[:starts[0]] + content[cut:], content[starts[0]:cut]))
    return plans


def rotate(root: Path, *, threshold: int = 200_000, keep: int = 3, apply: bool = False) -> int:
    plans = plan_rotation(root, threshold, keep)
    archive = root / "docs/archive"
    if plans and apply:
        if (root / "docs").is_symlink() or archive.is_symlink():
            raise ValueError("Refusing a symlinked archive directory")
        archive.mkdir(parents=True, exist_ok=True)
    for path, retained, old in plans:
        if apply:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            target = archive / f"{path.stem}-{stamp}.md"
            # Durable archive first; never overwrite an earlier archive.
            with target.open("x") as stream:
                stream.write(f"# Archived {path.name}\n\n{old}")
            temporary = path.with_name(f".{path.name}.rotation-tmp")
            created = False
            try:
                with temporary.open("x") as stream:
                    created = True
                    stream.write(retained)
                temporary.replace(path)
            finally:
                if created and temporary.exists():
                    temporary.unlink()
        print(f"{'Archived' if apply else 'Would archive'} older sections from {path.name}")
    if not plans:
        print("No workflow logs need rotation")
    return len(plans)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write archives; default is dry run")
    parser.add_argument("--threshold", type=int, default=200_000, help="Rotation size in bytes")
    parser.add_argument("--keep", type=int, default=3, help="Keep this many recent version sections")
    args = parser.parse_args()
    try:
        rotate(ROOT, threshold=args.threshold, keep=args.keep, apply=args.apply)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Rotation refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
