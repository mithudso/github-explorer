from contextlib import nullcontext

import pytest
from textual.widgets import Button, Input, TextArea, Tree

from github_explorer import catalog, runner
from github_explorer.app import GitHubExplorer
from github_explorer.panel import CommandConfirm

pytestmark = pytest.mark.usefixtures("ui_repository")


@pytest.fixture
def shortcuts(monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [])
    monkeypatch.setattr(runner, "git_executable", lambda: "/fixture/git")


@pytest.mark.parametrize("action", catalog.QUICK_ACTIONS, ids=lambda action: action.id)
async def test_button_and_hotkey_preview_cancel_and_execute(tmp_path, monkeypatch, shortcuts, action):
    calls = []

    def captured(self, invocation, on_output, timeout):
        calls.append((invocation, False))
        return runner.Result(0, "fixture output")

    def interactive(invocation):
        calls.append((invocation, True))
        return 0

    monkeypatch.setattr(runner.CommandRunner, "run", captured)
    monkeypatch.setattr(runner, "run_interactive", interactive)
    app = GitHubExplorer(tmp_path, repo="other/repo")
    monkeypatch.setattr(app, "suspend", lambda: nullcontext())
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        await pilot.click(f"#quick-{action.id}")
        assert isinstance(app.screen, CommandConfirm)
        first = app.screen.invocation
        assert first.argv == (f"/fixture/{action.argv[0]}", *action.argv[1:])
        assert first.cwd == tmp_path
        assert first.repo == ("other/repo" if action.argv[0] == "gh" else "")
        assert app.screen.interactive == action.interactive
        assert calls == []
        # A second shortcut must not replace an open confirmation.
        await pilot.press("f2")
        assert app.screen.invocation is first
        await pilot.press("escape")
        assert calls == []
        panel.query_one("#gh-command", TextArea).focus()
        await pilot.press(action.key)
        assert isinstance(app.screen, CommandConfirm)
        assert app.screen.invocation == first
        await pilot.click("#gh-confirm-run")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert calls == [(first, action.interactive)]
        assert panel.last_result.returncode == 0
        assert all(not button.disabled for button in panel.query("#gh-quick-buttons Button"))


async def test_git_menu_typing_and_busy_shortcuts(tmp_path, shortcuts):
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        panel = app.screen
        search = panel.query_one("#gh-search", Input)
        search.focus()
        await pilot.press(*"pull")
        assert search.value == "pull" and app.screen is panel
        tree = panel.query_one("#gh-tree", Tree)
        git = next(node for node in tree.root.children if "Git" in str(node.label))
        tree.select_node(git.children[0])
        await pilot.pause()
        assert panel.query_one("#gh-command", TextArea).text == "git pull --ff-only"
        panel.busy = True
        await pilot.press("f3")
        assert app.screen is panel
        assert panel.query_one("#gh-command", TextArea).text == "git pull --ff-only"
        panel.busy = False


@pytest.mark.parametrize("size", [(120, 40), (80, 32)])
async def test_shortcut_bar_fits_and_resizes(tmp_path, shortcuts, size):
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=size) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        for width, height in (size, (140, 45)):
            await pilot.resize_terminal(width, height)
            await pilot.pause()
            panel = app.screen
            buttons = list(panel.query("#gh-quick-buttons Button"))
            assert len(buttons) == 12
            for button in buttons:
                assert button.region.y >= panel.query_one("#gh-clear", Button).region.bottom
                assert button.region.bottom <= height
                assert button.region.right <= width
            assert len({(button.region.x, button.region.y) for button in buttons}) == 12
