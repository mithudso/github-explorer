#!/usr/bin/env python3
"""Stage npm payload and a checksummed Homebrew formula from the locked release."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def preflight_inputs(root: Path) -> None:
    """Keep build metadata, copied documents and source-archive inputs inside the repo."""
    paths = [root / name for name in [
        'README.md', 'LICENSE', 'NOTICE.md', 'pyproject.toml', 'uv.lock', 'MANIFEST.in',
        'npm/package.json', 'docs/operations-registry.json', 'docs/tool-inventory.json',
    ]]
    for name in ['src', 'scripts', 'tests']:
        directory = root / name
        paths.append(directory)
        if not directory.is_symlink():
            paths.extend(directory.rglob('*'))
    for path in paths:
        for component in (path, *path.parents):
            if component == root:
                break
            if component.is_symlink():
                raise ValueError(f'Refusing symlinked release input: {component.relative_to(root)}')


def preflight_outputs(root: Path, version: str) -> None:
    """Reject redirected writes and foreign staging material before building anything."""
    paths = [
        root / 'dist', root / f'dist/github_explorer-{version}-py3-none-any.whl',
        root / f'dist/github_explorer-{version}.tar.gz', root / 'npm/python',
        root / 'npm/python/requirements.txt',
        *(root / 'npm' / name for name in ['README.md', 'LICENSE', 'NOTICE.md']),
        root / 'packaging/homebrew/github-explorer.rb',
    ]
    payload = root / 'npm/python'
    for path in paths:
        for component in (path, *path.parents):
            if component == root:
                break
            if component.is_symlink():
                raise ValueError(f'Refusing symlinked release output: {component.relative_to(root)}')
    if payload.exists():
        for entry in payload.iterdir():
            owned = entry.name == 'requirements.txt' or (
                entry.name.startswith('github_explorer-')
                and entry.name.endswith('-py3-none-any.whl')
            )
            if entry.is_symlink() or not entry.is_file() or not owned:
                raise ValueError(f'Unexpected release staging entry: {entry.relative_to(root)}')


def main() -> None:
    preflight_inputs(ROOT)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    version = project["version"]
    npm = json.loads((ROOT / "npm/package.json").read_text())
    if npm["version"] != version:
        raise SystemExit("Python and npm versions differ")
    preflight_outputs(ROOT, version)
    subprocess.run(["uv", "build", "--quiet"], cwd=ROOT, check=True)
    payload = ROOT / "npm/python"
    payload.mkdir(parents=True, exist_ok=True)
    for old in payload.glob("*.whl"):
        old.unlink()
    shutil.copy2(ROOT / f"dist/github_explorer-{version}-py3-none-any.whl", payload)
    for name in ["README.md", "LICENSE", "NOTICE.md"]:
        shutil.copy2(ROOT / name, ROOT / "npm" / name)
    subprocess.run(
        ["uv", "export", "--frozen", "--no-dev", "--no-emit-project", "--no-hashes",
         "--no-header", "--no-annotate", "--output-file", str(payload / "requirements.txt")],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
    )
    # The export is the lockfile's runtime closure. Do not include dev/Windows-only packages.
    runtime = {
        line.split("==")[0]
        for line in (payload / "requirements.txt").read_text().splitlines()
        if "==" in line and "sys_platform == 'win32'" not in line
    }
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    resources = []
    for package in lock["package"]:
        if package["name"] in runtime:
            source = package["sdist"]
            resources.append(
                f'  resource "{package["name"]}" do\n'
                f'    url "{source["url"]}"\n'
                f'    sha256 "{source["hash"].removeprefix("sha256:")}"\n'
                '  end\n'
            )
    source = ROOT / f"dist/github_explorer-{version}.tar.gz"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    formula = '''class GithubExplorer < Formula
  include Language::Python::Virtualenv

  desc "Terminal workbench for GitHub with embedded Vim and Git commands"
  homepage "https://github.com/mithudso/github-explorer"
  url "https://github.com/mithudso/github-explorer/releases/download/vVERSION/github_explorer-VERSION.tar.gz"
  sha256 "DIGEST"
  license "MIT"

  depends_on "gh"
  depends_on "git"
  depends_on "python@3.14"
  depends_on "vim"

RESOURCES
  def install
    virtualenv_install_with_resources system_site_packages: false
  end

  test do
    assert_equal version.to_s, shell_output("#{bin}/github-explorer --version").strip
    assert_equal version.to_s, shell_output("#{bin}/ghx --version").strip
    assert_match "pr", shell_output("#{bin}/github-explorer --list-commands")
  end
end
'''.replace("VERSION", version).replace("DIGEST", digest).replace(
        "RESOURCES", "\n".join(resources)
    )
    (ROOT / "packaging/homebrew/github-explorer.rb").write_text(formula)
    print(f"Staged npm and Homebrew packages for {version}")


if __name__ == "__main__":
    main()
