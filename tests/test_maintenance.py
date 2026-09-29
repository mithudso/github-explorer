"""Regression checks for maintenance writes and static operation metadata."""

import importlib.util
from pathlib import Path

import pytest

from github_explorer.operations import get_operation, list_operations

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rotation_preserves_all_sections_and_defaults_to_dry_run(tmp_path):
    rotate = script("rotate_workflow_logs").rotate
    original = "# Prompts\nVersion: 4\n\n" + "".join(
        f"## Prompt v{i} - 2026-09-29\nrequest {i}\n" for i in range(1, 5)
    )
    path = tmp_path / "prompts.md"
    path.write_text(original)
    assert rotate(tmp_path, threshold=1, keep=2) == 1
    assert path.read_text() == original
    assert not (tmp_path / "docs/archive").exists()
    assert rotate(tmp_path, threshold=1, keep=2, apply=True) == 1
    retained = path.read_text()
    archived = next((tmp_path / "docs/archive").glob("*.md")).read_text()
    assert retained.startswith("# Prompts\nVersion: 4")
    for i in (1, 2):
        assert f"request {i}" in archived and f"request {i}" not in retained
    for i in (3, 4):
        assert f"request {i}" in retained and f"request {i}" not in archived
    assert rotate(tmp_path, threshold=1, keep=2, apply=True) == 0


def test_rotation_refuses_all_writes_when_either_log_has_editor_marker(tmp_path):
    rotate = script("rotate_workflow_logs").rotate
    path = tmp_path / "prompts.md"
    content = "## Prompt v1\none\n## Prompt v2\ntwo\n"
    path.write_text(content)
    (tmp_path / ".memory.md.swp").touch()
    with pytest.raises(ValueError, match="Editor marker"):
        rotate(tmp_path, threshold=1, keep=1, apply=True)
    assert path.read_text() == content
    assert not (tmp_path / "docs/archive").exists()


def test_rotation_ignores_heading_in_fenced_example(tmp_path):
    rotate = script("rotate_workflow_logs").rotate
    path = tmp_path / "memory.md"
    path.write_text("# Memory\n## v1\nold\n## v2\n```md\n## v99\nexample\n```\nlatest\n")
    rotate(tmp_path, threshold=1, keep=1, apply=True)
    assert "## v2" in path.read_text() and "latest" in path.read_text()
    assert "old" not in path.read_text()


def test_metadata_is_copied_and_generated_artifacts_are_current():
    original = get_operation("catalog-help")["remediation"]["timeout"]
    changed = list_operations()
    changed[0]["remediation"]["timeout"] = "modified by caller"
    assert get_operation("catalog-help")["remediation"]["timeout"] == original
    with pytest.raises(KeyError):
        get_operation("not-an-operation")
    for name, expected in script("generate_ops_registry_doc").render(ROOT).items():
        assert (ROOT / name).read_text() == expected, name


def test_operation_generator_refuses_symlink_before_any_output_write(tmp_path):
    write_outputs = script("generate_ops_registry_doc").write_outputs
    docs = tmp_path / "docs"
    docs.mkdir()
    external = tmp_path / "unrelated.json"
    external.write_text("keep me")
    (docs / "tool-inventory.json").symlink_to(external)
    with pytest.raises(ValueError, match="symlink"):
        write_outputs(tmp_path, {
            "docs/operations-registry.json": "new",
            "docs/tool-inventory.json": "overwrite",
        })
    assert external.read_text() == "keep me"
    assert not (docs / "operations-registry.json").exists()


def test_rotation_preserves_preexisting_temporary_file(tmp_path):
    rotate = script("rotate_workflow_logs").rotate
    path = tmp_path / "prompts.md"
    original = "## Prompt v1\none\n## Prompt v2\ntwo\n"
    path.write_text(original)
    temporary = tmp_path / ".prompts.md.rotation-tmp"
    temporary.write_text("recovery state")
    with pytest.raises(FileExistsError):
        rotate(tmp_path, threshold=1, keep=1, apply=True)
    assert temporary.read_text() == "recovery state"
    assert path.read_text() == original
