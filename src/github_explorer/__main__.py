from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .app import GitHubExplorer
from .catalog import executable, load_catalog
from .runner import re_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="github-explorer",
        description="Explore and run the installed GitHub CLI in a terminal UI",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Repository working directory")
    parser.add_argument("--repo", default="", help="Optional [HOST/]OWNER/REPO override")
    parser.add_argument(
        "--list-commands", action="store_true", help="Print the local gh catalog as JSON"
    )
    args = parser.parse_args(argv)
    cwd = args.cwd.expanduser().absolute()
    if not cwd.is_dir():
        parser.error(f"Working directory does not exist: {cwd}")
    if args.repo and not re_repo(args.repo):
        parser.error("Repository must be OWNER/REPO or HOST/OWNER/REPO")
    try:
        executable()
        if args.list_commands:
            print(
                json.dumps(
                    [
                        {"command": c.name, "description": c.summary, "external": c.external}
                        for c in load_catalog(cwd)
                    ],
                    indent=2,
                )
            )
        else:
            GitHubExplorer(cwd, args.repo).run()
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
