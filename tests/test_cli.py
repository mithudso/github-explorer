import json
import subprocess

import pytest
from textual.widgets import Button, Label

from github_explorer import GitHubExplorer, GitHubPanel, __version__, catalog
from github_explorer import __main__ as cli


def test_help_and_version_need_no_github_install(monkeypatch, capsys):
    monkeypatch.setattr(cli, "executable", lambda: pytest.fail("must not inspect gh"))
    for flag in ["--version", "--help"]:
        with pytest.raises(SystemExit) as result:
            cli.main([flag])
        assert result.value.code == 0
    output = capsys.readouterr().out
    assert __version__ in output
    assert "--list-commands" in output


def test_invalid_context_and_missing_gh(tmp_path, monkeypatch, capsys):
    for args in [["--cwd", str(tmp_path / "missing")], ["--repo", "invalid"]]:
        with pytest.raises(SystemExit) as result:
            cli.main(args)
        assert result.value.code == 2

    def missing():
        raise ValueError("gh is not installed")

    monkeypatch.setattr(cli, "executable", missing)
    with pytest.raises(SystemExit) as result:
        cli.main(["--cwd", str(tmp_path)])
    assert result.value.code == 1
    assert "gh is not installed" in capsys.readouterr().err


def test_catalog_export_never_starts_tui(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "executable", lambda: "/mock/gh")
    monkeypatch.setattr(
        cli,
        "load_catalog",
        lambda path: [catalog.Command(("repo", "view"), "View a repository", "help")],
    )
    monkeypatch.setattr(GitHubExplorer, "run", lambda self: pytest.fail("must not start UI"))
    assert cli.main(["--cwd", str(tmp_path), "--list-commands"]) == 0
    assert json.loads(capsys.readouterr().out) == [
        {"command": "repo view", "description": "View a repository", "external": False}
    ]


def test_catalog_timeout_exits_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "executable", lambda: "/mock/gh")
    monkeypatch.setattr(catalog, "executable", lambda: "/mock/gh")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(catalog.subprocess, "run", timeout)
    with pytest.raises(SystemExit) as result:
        cli.main(["--cwd", str(tmp_path), "--list-commands"])
    assert result.value.code == 1
    assert "timed out" in capsys.readouterr().err


async def test_standalone_host_branding_context_and_quit(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [])
    app = GitHubExplorer(tmp_path, "owner/repository")
    async with app.run_test(size=(140, 52)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert isinstance(app.screen, GitHubPanel)
        assert app.screen.repo_path == tmp_path
        assert app.screen.repo == "owner/repository"
        assert str(app.screen.query_one("#gh-title", Label).render()).startswith("GitHub Explorer")
        assert str(app.screen.query_one("#gh-close", Button).label) == "Quit"
        await pilot.click("#gh-close")
        await pilot.pause()
        assert app.return_value is None
