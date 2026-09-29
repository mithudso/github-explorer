#!/usr/bin/env python3
"""Generate public operation metadata without importing the application or invoking gh."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(root: Path) -> dict[str, str]:
    tree = ast.parse((root / "src/github_explorer/operations.py").read_text())
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "OPERATIONS" for target in node.targets)
    )
    operations = ast.literal_eval(assignment.value)
    for operation in operations:
        if not (root / operation["sourceFile"]).is_file():
            raise ValueError(f"Missing operation source: {operation['sourceFile']}")
    registry = {
        "schemaVersion": 1,
        "generatedBy": "scripts/generate_ops_registry_doc.py",
        "operations": operations,
        "status": "adapted-desktop-inventory",
        "audit": {
            "fullFiveStandardContract": False,
            "reason": "Local TUI has no service dashboard or datastore. Persistent command logs "
            "conflict with the project's privacy contract. This is metadata, not a dispatcher.",
            "remediation": "Human guidance only; keys classify outcomes, not runtime error codes.",
            "verification": "The app does not own a datastore. gh may change external state; "
            "the user must verify those changes before retrying.",
        },
    }
    inventory = {
        "schemaVersion": 1,
        "generatedBy": "scripts/generate_ops_registry_doc.py",
        "totalTools": 0,
        "tools": [],
        "reason": "The application exposes no MCP tools or HTTP routes.",
    }
    return {
        "docs/operations-registry.json": json.dumps(registry, indent=2) + "\n",
        "docs/tool-inventory.json": json.dumps(inventory, indent=2) + "\n",
    }


def write_outputs(root: Path, outputs: dict[str, str]) -> None:
    """Refuse symlinked output paths before writing either generated artifact."""
    for name in outputs:
        path = root / name
        if any(part.is_symlink() for part in (path, *path.parents) if part != root):
            raise ValueError(f"Refusing symlinked output path: {name}")
    for name, content in outputs.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated files differ")
    args = parser.parse_args()
    outputs = render(ROOT)
    stale = []
    for name, text in outputs.items():
        path = ROOT / name
        if args.check:
            if not path.is_file() or path.read_text() != text:
                stale.append(name)
    if not args.check:
        try:
            write_outputs(ROOT, outputs)
        except (OSError, ValueError) as exc:
            parser.exit(1, f"Generation refused: {exc}\n")
    if stale:
        print("Stale: " + ", ".join(stale))
        print("Regenerate with: python3 scripts/generate_ops_registry_doc.py")
        return 1
    print(f"Operation metadata {'checked' if args.check else 'generated'}: {len(outputs)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
