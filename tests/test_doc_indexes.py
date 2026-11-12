"""Exercise stale, deleted and newly added sources in isolated fixture repositories."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("check_doc_indexes", SCRIPTS / "check_doc_indexes.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
generator = sys.modules["generate_repo_indexes"]


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-b", "main")
    (tmp_path / "README.md").write_text("# Fixture\nPublic fixture.\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "fixture"\nversion = "1.0"\n')
    (tmp_path / ".gitignore").write_text("local-state/\n")
    git("add", ".")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
    return tmp_path


def test_generation_is_deterministic_and_does_not_index_its_outputs(repo):
    generator.write(repo)
    first = {p: (repo / p).read_bytes() for p in generator.OUTPUTS}
    assert checker.check(repo) == []
    generator.write(repo, refresh=True)
    assert first == {p: (repo / p).read_bytes() for p in generator.OUTPUTS}
    assert not set(generator.OUTPUTS) & set(generator.census(repo))


def test_changed_source_is_stale(repo):
    generator.write(repo)
    (repo / "README.md").write_text("# Modified\n")
    assert any("Stale generated file" in error for error in checker.check(repo))


def test_deleted_source_and_new_source_are_reported(repo):
    generator.write(repo)
    (repo / "README.md").unlink()
    (repo / "new.md").write_text("New public file.\n")
    errors = checker.check(repo)
    assert "Deleted or excluded source path: README.md" in errors
    assert "Missing indexed source path: new.md" in errors


def test_missing_output_and_tampered_filemap_are_reported(repo):
    generator.write(repo)
    (repo / "docs/llms/llms-small.txt").unlink()
    (repo / "docs/llms/filemap.json").write_text("[]\n")
    errors = checker.check(repo)
    assert "Missing generated file: docs/llms/llms-small.txt" in errors
    assert "Stale generated file: docs/llms/filemap.json" in errors


def test_private_ignored_files_and_symlinks_are_excluded(repo):
    (repo / ".env").write_text("SECRET=private\n")
    (repo / "local-state").mkdir()
    (repo / "local-state/private.md").write_text("private\n")
    (repo / "shortcut.md").symlink_to(repo / "README.md")
    (repo / "AGENTS.md").write_text("PRIVATE INSTRUCTION TEXT\n")
    (repo / ".env.example").write_text("TOKEN=EXAMPLE VALUE MUST STAY PRIVATE\n")
    generator.write(repo)
    assert ".env" not in generator.census(repo)
    assert "shortcut.md" not in generator.census(repo)
    assert "local-state/private.md" not in generator.census(repo)
    assert "AGENTS.md" in generator.census(repo)
    assert ".env.example" in generator.census(repo)
    for path in generator.OUTPUTS:
        assert "PRIVATE INSTRUCTION TEXT" not in (repo / path).read_text()
        assert "EXAMPLE VALUE MUST STAY PRIVATE" not in (repo / path).read_text()


def test_tracked_source_directory_replaced_by_symlink_is_excluded(repo, tmp_path_factory):
    directory = repo / "reference"
    directory.mkdir()
    source = directory / "note.md"
    source.write_text("Public original\n")
    subprocess.run(["git", "-C", str(repo), "add", "reference/note.md"], check=True)
    outside = tmp_path_factory.mktemp("private-source")
    (outside / "note.md").write_text("PRIVATE OUTSIDE CONTENT\n")
    source.unlink()
    directory.rmdir()
    directory.symlink_to(outside, target_is_directory=True)

    assert "reference/note.md" not in generator.census(repo)
    generator.write(repo)
    for path in generator.OUTPUTS:
        assert "PRIVATE OUTSIDE CONTENT" not in (repo / path).read_text()


def test_collision_requires_owned_manifest_and_explicit_refresh(repo):
    output = repo / "docs/llms"
    output.mkdir(parents=True)
    (output / "foreign.txt").write_text("existing material")
    with pytest.raises(ValueError, match="without a generator manifest"):
        generator.write(repo)
    (output / "foreign.txt").unlink()
    generator.write(repo)
    with pytest.raises(ValueError, match="requires --refresh"):
        generator.write(repo)


def test_manifest_and_caps(repo):
    generator.write(repo)
    manifest = json.loads((repo / "docs/llms/manifest.json").read_text())
    cards = json.loads((repo / "docs/llms/filemap.json").read_text())
    assert manifest["census"]["enumerated"] == len(cards)
    assert manifest["files"] == [card["path"] for card in cards]
    assert len((repo / "docs/llms/llms.txt").read_bytes()) <= 2000
    assert len((repo / "docs/llms/llms-small.txt").read_bytes()) <= 8000
    for output in repo.glob("docs/llms/*.txt"):
        lines = output.read_text().splitlines()
        assert lines[0].startswith("# github-explorer")
        assert lines[1].startswith("> Source:")
        assert lines[2].startswith("> Generated:")
        assert lines[3].startswith("> Census:")


def test_options_are_extracted_without_importing_code():
    source = '''raise RuntimeError("must not execute")
parser.add_argument("--sample", type=int, default=7)
'''
    inventory = generator.code_inventory("fixture.py", source)
    assert inventory["options"] == [{
        "definition": 'parser.add_argument("--sample", type=int, default=7)',
        "source": "fixture.py:2",
    }]


def test_remote_credentials_are_not_published():
    assert generator.safe_remote("https://secret@github.com/owner/repo.git") == "no-public-remote"
    assert generator.safe_remote("git@github.com:owner/repo.git") == "https://github.com/owner/repo"
    assert generator.safe_remote("https://github.com/owner/repo.git?token=secret#secret") == "https://github.com/owner/repo"


def test_generation_refuses_symlinked_output_directory(repo, tmp_path_factory):
    outside = tmp_path_factory.mktemp("external-documents")
    (repo / "docs").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinked generated path"):
        generator.write(repo)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize('name', ['AGENTS.md', 'CLAUDE.md', 'prompts.md', 'memory.md'])
def test_nested_private_document_bodies_are_never_extracted(repo, name):
    directory = repo / 'docs' / 'nested'
    directory.mkdir(parents=True)
    (directory / name).write_text('# PRIVATE NESTED HEADING\nhttps://private.invalid/secret\n')
    for content in generator.render(repo).values():
        assert 'PRIVATE NESTED HEADING' not in content
        assert 'private.invalid/secret' not in content


@pytest.mark.parametrize('name', ['notes#draft.md', 'why?.md', '100%.md', 'with space.md', 'café.md'])
def test_public_source_links_encode_path_and_branch(repo, name):
    (repo / name).write_text('Public note.\n')
    metadata = generator.snapshot(repo)
    metadata.update(remote='https://github.com/example/fixture', branch='feature/a#b')
    outputs = generator.render(repo, metadata)
    cards = json.loads(outputs['docs/llms/filemap.json'])
    link = next(card['link'] for card in cards if card['path'] == name)
    assert link == f"https://github.com/example/fixture/blob/{quote(metadata['branch'], safe='')}/{quote(name, safe='/')}"
    assert not urlsplit(link).fragment and not urlsplit(link).query


@pytest.mark.parametrize('name', ['docs/codebase-overview.md', 'docs/high_signal_file_index.json'])
@pytest.mark.parametrize('refresh', [False, True])
def test_foreign_top_level_outputs_are_preserved_before_any_write(repo, name, refresh):
    target = repo / name
    target.parent.mkdir(parents=True)
    target.write_text('Foreign material to preserve.\n')
    with pytest.raises(ValueError, match='without a generator manifest'):
        generator.write(repo, refresh=refresh)
    assert target.read_text() == 'Foreign material to preserve.\n'
    assert not (repo / 'docs/llms').exists()


def test_ci_inventory_reads_named_scalar_literal_and_folded_steps(repo):
    workflows = repo / '.github/workflows'
    workflows.mkdir(parents=True)
    (workflows / 'checks.yml').write_text('''jobs:
  check:
    steps:
      - name: Scalar command
        run: uv run pytest
      - run: |
          uv run ruff check .
          uv build
      - name: Folded command
        run: >-
          uv run python
          scripts/check_doc_indexes.py
''')
    output = generator.render(repo)['docs/llms/llms-executable.txt']
    assert '`uv run pytest`' in output
    assert 'uv run ruff check .\nuv build' in output
    assert 'uv run python scripts/check_doc_indexes.py' in output
    assert '`|`' not in output and '`>-`' not in output


def test_checker_reports_unreadable_output_with_refresh_guidance(repo, monkeypatch, capsys):
    generator.write(repo)
    (repo / 'docs/llms/llms.txt').write_bytes(b'\xff')
    errors = checker.check(repo)
    assert any('docs/llms/llms.txt' in error for error in errors)
    monkeypatch.setattr(checker, 'ROOT', repo)
    assert checker.main() == 1
    assert 'Refresh with:' in capsys.readouterr().out


def test_executable_inventory_includes_npm_launchers_and_scripts(repo):
    (repo / 'npm').mkdir()
    (repo / 'npm/package.json').write_text(json.dumps({
        'name': '@example/fixture',
        'bin': {'fixture': 'bin/fixture.cjs'},
        'scripts': {'test': 'node --test test/*.cjs'},
    }))
    output = generator.render(repo)['docs/llms/llms-executable.txt']
    assert 'npm/bin/fixture.cjs' in output
    assert 'npm --prefix npm run test' in output
    assert 'node --test test/*.cjs' in output
