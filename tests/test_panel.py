import asyncio
import threading
from contextlib import nullcontext

from textual.app import App
from textual.widgets import Input, RichLog, Select, TextArea, Tree

from github_explorer import GitHubPanel, catalog, runner
from github_explorer.panel import CommandConfirm


class Host(App):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def on_mount(self):
        self.push_screen(GitHubPanel(self.path))


async def test_embed_catalog_flags_preview_run_and_return(tmp_path, monkeypatch):
    flags = (catalog.Flag("--title", "string", "Title"), catalog.Flag("--draft"))
    commands = [
        catalog.Command(("pr",), "Pull requests", "pr help"),
        catalog.Command(("pr", "create"), "Create pull request", "create help", flags),
    ]
    monkeypatch.setattr(catalog, "load_catalog", lambda path: commands)
    monkeypatch.setattr(runner, "executable", lambda: "/mock/gh")
    calls = []

    def run(self, invocation, on_output, timeout):
        calls.append(invocation)
        on_output("created fixture PR")
        return runner.Result(0, "created fixture PR")

    monkeypatch.setattr(runner.CommandRunner, "run", run)
    app = Host(tmp_path)
    copied = []
    monkeypatch.setattr(app, "copy_to_clipboard", copied.append)
    async with app.run_test(size=(140, 52)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        tree = panel.query_one("#gh-tree", Tree)
        tree.select_node(tree.root.children[0].children[0])
        await pilot.pause()
        assert "gh pr create" == panel.query_one("#gh-command", TextArea).text
        panel.query_one("#gh-flag", Select).value = 0
        panel.query_one("#gh-value", Input).value = "Title with spaces"
        await pilot.click("#gh-add-flag")
        await pilot.click("#gh-run")
        await pilot.pause()
        assert isinstance(app.screen, CommandConfirm)
        assert calls == []
        await pilot.click("#gh-confirm-cancel")
        await pilot.pause()
        assert calls == []
        await pilot.click("#gh-run")
        await pilot.click("#gh-confirm-run")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert calls[0].argv[-2:] == ("--title", "Title with spaces")
        assert panel.last_result.returncode == 0
        assert copied == []
        await pilot.click("#gh-copy")
        assert copied == ["created fixture PR"]
        await pilot.click("#gh-clear")
        assert panel.last_result is None
        assert not panel.query_one("#gh-log", RichLog).lines
        monkeypatch.setattr(app, "suspend", lambda: nullcontext())
        monkeypatch.setattr(runner, "run_interactive", lambda invocation: 0)
        await pilot.click("#gh-terminal")
        await pilot.click("#gh-confirm-run")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert panel.last_result.returncode == 0
        await pilot.press("escape")
        assert app.screen is not panel


async def test_stop_keeps_panel_until_command_ends(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda path: [])
    monkeypatch.setattr(runner, "executable", lambda: "/mock/gh")

    released = threading.Event()

    def run(self, invocation, on_output, timeout):
        assert self.cancelled.wait(5)
        assert released.wait(5)
        return runner.Result(-9, "stopped", cancelled=True)

    monkeypatch.setattr(runner.CommandRunner, "run", run)
    app = Host(tmp_path)
    async with app.run_test(size=(140, 52)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        await pilot.click("#gh-run")
        await pilot.click("#gh-confirm-run")
        await pilot.pause()
        assert panel.busy
        await pilot.press("escape")
        assert app.screen is panel
        try:
            await pilot.click("#gh-stop")
            assert panel.busy
        finally:
            released.set()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert panel.last_result.cancelled and not panel.busy


async def test_reload_ignores_cancelled_catalog_result(tmp_path, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    old = [catalog.Command(("old",), "Old catalog", "old help")]
    new = [catalog.Command(("new",), "New catalog", "new help")]
    calls = []

    def load(path):
        calls.append(path)
        if len(calls) == 1:
            started.set()
            assert release.wait(5)
            return old
        return new

    monkeypatch.setattr(catalog, "load_catalog", load)
    app = Host(tmp_path)
    async with app.run_test(size=(140, 52)) as pilot:
        try:
            assert await asyncio.to_thread(started.wait, 5)
            panel = app.screen
            worker = panel.load_commands()
            await worker.wait()
            await pilot.pause()
            assert panel.commands == new
        finally:
            release.set()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert panel.commands == new
