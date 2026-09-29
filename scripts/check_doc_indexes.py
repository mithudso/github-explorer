"""Check source paths, hashes and generated documentation without application probes."""

from __future__ import annotations

import json
from pathlib import Path

from generate_repo_indexes import OUTPUTS, ROOT, census, render


def check(root: Path) -> list[str]:
    missing_outputs = [p for p in OUTPUTS if not (root / p).is_file()]
    errors = [f"Missing generated file: {p}" for p in missing_outputs]
    manifest_path = root / "docs/llms/manifest.json"
    if not manifest_path.exists():
        return errors
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        recorded = set(manifest["files"])
        actual = set(census(root))
        errors.extend(f"Deleted or excluded source path: {p}" for p in sorted(recorded - actual))
        errors.extend(f"Missing indexed source path: {p}" for p in sorted(actual - recorded))
        metadata = {key: manifest[key] for key in (
            "source", "remote", "commit", "branch", "generated_at", "dirty", "history",
        )}
        expected = render(root, metadata)
    except (ValueError, KeyError, TypeError, OSError, SyntaxError) as exc:
        return [*errors, f"Invalid source or manifest: {exc}"]
    for path, content in expected.items():
        if path not in missing_outputs and (root / path).read_text(encoding="utf-8") != content:
            errors.append(f"Stale generated file: {path}")
    return errors


def main() -> int:
    errors = check(ROOT)
    if errors:
        print("\n".join(errors))
        print("Refresh with: python scripts/generate_repo_indexes.py --refresh")
        return 1
    print("Static documentation indexes match the public source census.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
