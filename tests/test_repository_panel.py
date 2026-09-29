import asyncio
import threading

import pytest
from textual.widgets import Button, Checkbox, Input, Select, Static, TabbedContent, TextArea, Tree

from github_explorer import GitHubExplorer, catalog, runner
from github_explorer.panel import CommandConfirm, RepoSettings

pytestmark = pytest.mark.usefixtures("ui_repository")


async def test_files_are_above_catalog_default_search_and_preview(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [])
    files = [
        {"path": "README.md", "type": "blob", "sha": "readme"},
        {"path": "src/main.py", "type": "blob", "sha": "main"},
    ]
    monkeypatch.setattr(runner, "repository_files", lambda repo, executor: files)
    previews = []
    def preview(repo, entry, executor):
        previews.append(entry["path"])
        return "print('fixture')"
    monkeypatch.setattr(runner, "repository_file_text", preview)
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(140, 52)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        tree = panel.query_one("#gh-files", Tree)
        assert panel.query_one("#gh-tabs", TabbedContent).active == "gh-files-tab"
        assert tree.region.y < panel.query_one("#gh-tree", Tree).region.y
        assert tree.has_focus
        assert len(tree.root.children) == 2
        panel.query_one("#gh-file-search", Input).value = "main.py"
        await pilot.pause()
        assert str(tree.root.children[0].label) == "src"
        tree.select_node(tree.root.children[0].children[0])
        await pilot.pause()
        await app.workers.wait_for_complete()
        assert panel.query_one("#gh-file-preview", TextArea).text == "print('fixture')"
        assert previews == ["src/main.py"]
        panel.query_one("#gh-repo", Input).value = "different/repo"
        tree.select_node(tree.root.children[0].children[0])
        await pilot.pause()
        assert previews == ["src/main.py"]
        assert "Refresh files" in str(panel.query_one("#gh-status", Static).render())


async def test_settings_current_values_cancel_and_confirm_exact_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [])
    flags = (catalog.Flag("--description", "string", "Description"),
             catalog.Flag("--enable-issues", "", "Issues"),
             catalog.Flag("--future-setting", "string", "New setting"))
    monkeypatch.setattr(catalog, "repository_settings", lambda cwd: flags)
    calls = []
    def run(self, invocation, on_output, timeout):
        calls.append(invocation)
        return runner.Result(0, "")
    monkeypatch.setattr(runner.CommandRunner, "run", run)
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(140, 52)) as pilot:
        await app.workers.wait_for_complete()
        panel = app.screen
        await pilot.click("#gh-settings")
        await app.workers.wait_for_complete()
        await pilot.pause()
        settings = app.screen
        assert isinstance(settings, RepoSettings)
        assert len(settings.flags) == 3
        assert settings.query_one("#setting-value-0", Input).value == "Fixture description"
        assert settings.query_one("#setting-value-1", Select).value == "true"
        assert settings.query_one("#setting-value-2", Input).value == ""
        settings.query_one("#setting-change-0", Checkbox).value = True
        settings.query_one("#setting-value-0", Input).value = ""
        settings.query_one("#setting-change-1", Checkbox).value = True
        settings.query_one("#setting-value-1", Select).value = "false"
        # A context edit behind the modal cannot redirect a confirmed change.
        panel.query_one("#gh-repo", Input).value = "different/repo"
        await pilot.click("#settings-review")
        await pilot.pause()
        assert isinstance(app.screen, CommandConfirm)
        assert calls == []
        assert app.screen.invocation.repo == "github.com/owner/repository"
        await pilot.click("#gh-confirm-cancel")
        await pilot.pause()
        assert app.screen is settings and calls == []
        assert settings.query_one("#setting-change-1", Checkbox).value
        await pilot.click("#settings-review")
        await pilot.click("#gh-confirm-run")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.screen is panel
        assert len(calls) == 1
        assert calls[0].argv[-2:] == ("--description=", "--enable-issues=false")
        assert "--future-setting" not in " ".join(calls[0].argv)
        assert calls[0].cwd == tmp_path.resolve()
        assert calls[0].repo == "github.com/owner/repository"
        assert not panel.busy


async def test_failed_repository_read_leaves_cli_usable(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [catalog.Command(("repo",), "Repo", "help")])
    def fail(context, executor):
        raise ValueError("Repository inaccessible; check authentication")
    monkeypatch.setattr(runner, "repository_info", fail)
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        assert "inaccessible" in str(panel.query_one("#gh-file-status", Static).render())
        assert panel.query_one("#gh-tree", Tree).root.children
        await pilot.click("#gh-settings")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.screen.query_one("#settings-review", Button).disabled
        assert "inaccessible" in str(app.screen.query_one("#settings-status", Static).render())
        await pilot.press("escape")
        assert app.screen is panel


async def test_late_file_read_cannot_replace_refreshed_repository(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [])
    started, release = threading.Event(), threading.Event()
    calls = []
    def files(repository, executor):
        calls.append(repository)
        if len(calls) == 1:
            started.set()
            assert release.wait(5)
            return [{"path": "old.md", "type": "blob", "sha": "old"}]
        return [{"path": "new.md", "type": "blob", "sha": "new"}]
    monkeypatch.setattr(runner, "repository_files", files)
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(140, 52)) as pilot:
        try:
            assert await asyncio.to_thread(started.wait, 5)
            panel = app.screen
            await pilot.click("#gh-refresh-files")
            await pilot.pause()
            assert [entry["path"] for entry in panel.files] == ["new.md"]
        finally:
            release.set()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert [entry["path"] for entry in panel.files] == ["new.md"]


async def test_visibility_requires_explicit_acceptance_before_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [])
    flags = (catalog.Flag("--visibility", "string"),
             catalog.Flag("--accept-visibility-change-consequences"))
    monkeypatch.setattr(catalog, "repository_settings", lambda cwd: flags)
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.click("#gh-settings")
        await app.workers.wait_for_complete()
        await pilot.pause()
        settings = app.screen
        assert settings.query_one("#setting-value-1", Select).value is Select.NULL
        settings.query_one("#setting-change-0", Checkbox).value = True
        settings.query_one("#setting-value-0", Input).value = "private"
        await pilot.click("#settings-review")
        await pilot.pause()
        assert app.screen is settings
        assert "accept-visibility-change-consequences" in str(settings.query_one("#settings-status", Static).render())
        settings.query_one("#setting-change-1", Checkbox).value = True
        settings.query_one("#setting-value-1", Select).value = "true"
        await pilot.pause(0.4)  # Review ignores clicks during its active animation.
        await pilot.click("#settings-review")
        await pilot.pause()
        assert isinstance(app.screen, CommandConfirm)
        assert app.screen.invocation.argv[-2:] == (
            "--visibility=private", "--accept-visibility-change-consequences=true",
        )
        await pilot.press("escape")
        assert app.screen is settings
        await pilot.press("escape")
        assert app.screen is not settings


async def test_late_preview_cannot_replace_new_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [])
    monkeypatch.setattr(runner, "repository_files", lambda repo, executor: [
        {"path": "a.md", "type": "blob", "sha": "a"},
        {"path": "b.md", "type": "blob", "sha": "b"},
    ])
    started, release = threading.Event(), threading.Event()
    def preview(repository, entry, executor):
        if entry["sha"] == "a":
            started.set()
            assert release.wait(5)
        return entry["path"]
    monkeypatch.setattr(runner, "repository_file_text", preview)
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        panel = app.screen
        tree = panel.query_one("#gh-files", Tree)
        try:
            tree.select_node(tree.root.children[0])
            await pilot.pause()
            assert await asyncio.to_thread(started.wait, 5)
            tree.select_node(tree.root.children[1])
            await pilot.pause()
            assert panel.query_one("#gh-file-preview", TextArea).text == "b.md"
        finally:
            release.set()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert panel.query_one("#gh-file-preview", TextArea).text == "b.md"
