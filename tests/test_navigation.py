import pytest
from textual.widgets import Button, Input, Select, TextArea, Tree

from github_explorer import catalog, runner
from github_explorer.app import GitHubExplorer
from github_explorer.panel import CommandConfirm, RepoSettings

pytestmark = pytest.mark.usefixtures("ui_repository")


@pytest.fixture
def navigation(monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [
        catalog.Command(("pr", "list"), "PR list", "help"),
        catalog.Command(("repo", "view"), "View", "help"),
    ])
    monkeypatch.setattr(runner, "repository_files", lambda repository, executor: [
        {"path": "docs/a.md", "type": "blob", "sha": "fixture-a"},
        {"path": "README.md", "type": "blob", "sha": "fixture-b"},
    ])


@pytest.mark.parametrize("tree_id", ["gh-files", "gh-tree"])
async def test_tree_arrows_expand_walk_collapse_without_selecting(tmp_path, navigation, tree_id):
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        tree = panel.query_one(f"#{tree_id}", Tree)
        branch = tree.root.children[0]
        tree.move_cursor(branch)
        tree.focus()
        await pilot.press("down")
        assert branch.is_expanded and tree.cursor_node is branch
        await pilot.press("down")
        assert tree.cursor_node is branch.children[0]
        await pilot.press("down")
        assert tree.cursor_node is tree.root.children[1]
        await pilot.press("up", "left")
        assert tree.cursor_node is branch
        await pilot.press("left")
        assert not branch.is_expanded
        await pilot.press("right")
        assert branch.is_expanded
        await pilot.press("right")
        assert tree.cursor_node is branch.children[0]
        assert panel.query_one("#gh-command", TextArea).text == "gh repo view"
        assert panel.query_one("#gh-file-preview", TextArea).text == ""


async def test_spatial_buttons_fields_and_dropdown(tmp_path, navigation):
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        panel = app.screen
        panel.query_one("#quick-status", Button).focus()
        await pilot.press("right")
        assert app.focused.id == "quick-pull"
        await pilot.press("down")
        assert app.focused.id == "quick-pr"
        await pilot.press("left")
        assert app.focused.id == "quick-commit"
        await pilot.press("up")
        assert app.focused.id == "quick-status"
        # Inputs retain horizontal editing; vertical arrows leave the field.
        field = panel.query_one("#gh-search", Input)
        field.focus()
        await pilot.press(*"pull", "left", "X")
        assert field.value == "pulXl"
        await pilot.press("down")
        assert app.focused.id == "gh-tree"
        select = panel.query_one("#gh-flag", Select)
        select.set_options([("One", 1), ("Two", 2)])
        select.focus()
        await pilot.press("down")
        assert select.expanded
        await pilot.press("down", "enter")
        assert select.value == 1 and not select.expanded
        # Arrows in the editor only edit; they don't move focus or execute.
        editor = panel.query_one("#gh-command", TextArea)
        editor.load_text("gh repo view\n--json name")
        editor.focus()
        await pilot.press("down", "left", "up", "right")
        assert app.focused is editor and app.screen is panel


async def test_settings_and_confirmation_arrows(tmp_path, monkeypatch, navigation):
    monkeypatch.setattr(catalog, "repository_settings", lambda path: (
        catalog.Flag("--enable-issues", "", "Issues"),
        catalog.Flag("--description", "string", "Description"),
    ))
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.click("#gh-settings")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert isinstance(app.screen, RepoSettings)
        app.screen.query_one("#setting-change-0").focus()
        await pilot.press("right")
        assert app.focused.id == "setting-value-0"
        await pilot.press("down")
        assert app.screen.query_one("#setting-value-0", Select).expanded
        await pilot.press("enter")
        app.screen.query_one("#settings-review", Button).focus()
        await pilot.press("right")
        assert app.focused.id == "settings-close"
        await pilot.press("escape")
        await pilot.click("#gh-run")
        assert isinstance(app.screen, CommandConfirm)
        app.screen.query_one("#gh-confirm-run", Button).focus()
        await pilot.press("right")
        assert app.focused.id == "gh-confirm-cancel"
        await pilot.press("left")
        assert app.focused.id == "gh-confirm-run"
        await pilot.press("escape")
        assert app.screen.last_result is None


async def test_tree_boundaries_and_readonly_content_allow_arrow_exit(tmp_path, navigation):
    from textual.widgets import RichLog, TabbedContent

    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        tree = panel.query_one("#gh-files", Tree)
        tree.move_cursor(tree.root.children[-1])
        tree.focus()
        await pilot.press("down")
        assert app.focused.id == "gh-search"
        tree.move_cursor(tree.root)
        tree.focus()
        await pilot.press("up")
        assert app.focused.id == "gh-file-search"
        panel.query_one("#gh-terminal", Button).focus()
        await pilot.press("right")
        assert app.focused.id == "gh-close"  # Skip disabled Stop.
        preview = panel.query_one("#gh-file-preview", TextArea)
        preview.load_text("first\nlast")
        preview.focus()
        await pilot.press("down")
        assert app.focused is preview and preview.cursor_location[0] == 1
        await pilot.press("down")
        assert isinstance(app.focused, Button)
        panel.query_one("#gh-tabs", TabbedContent).active = "gh-output-tab"
        await pilot.pause()
        log = panel.query_one("#gh-log", RichLog)
        for index in range(100):
            log.write(f"Fixture line {index}")
        log.focus()
        await pilot.pause()
        log.scroll_home(animate=False)
        await pilot.pause()
        await pilot.press("down")
        assert app.focused is log and log.scroll_y > 0
        log.scroll_end(animate=False)
        await pilot.pause()
        await pilot.press("down")
        assert isinstance(app.focused, Button)
