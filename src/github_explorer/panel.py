"""Reusable GitHub control screen. Depends only on Textual and this package."""

from __future__ import annotations

import shlex
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
    Tree,
)
from textual.worker import get_current_worker

from . import catalog, runner


class CommandConfirm(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    CommandConfirm { align: center middle; }
    CommandConfirm > Vertical { width: 100; max-width: 95%; height: auto;
        max-height: 90%; border: round $primary; padding: 1 2; background: $surface; }
    CommandConfirm TextArea { height: 12; }
    CommandConfirm Horizontal { height: 3; }
    """

    def __init__(self, invocation: runner.Invocation, interactive: bool):
        super().__init__()
        self.invocation, self.interactive = invocation, interactive

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                "Run GitHub command in terminal?" if self.interactive else "Run GitHub command?"
            )
            yield TextArea(self.invocation.preview, read_only=True)
            with Horizontal():
                yield Button("Run", variant="primary", id="gh-confirm-run")
                yield Button("Cancel", id="gh-confirm-cancel")

    @on(Button.Pressed)
    def choose(self, event: Button.Pressed):
        event.stop()
        self.dismiss(event.button.id == "gh-confirm-run")

    def action_cancel(self):
        self.dismiss(False)


class GitHubPanel(Screen):
    """Push onto any Textual 8 App; Escape returns to the host TUI.

    repo_path is the actual working directory used for gh. repo is an optional
    OWNER/REPO or HOST/OWNER/REPO GH_REPO override. Nothing runs on entry except
    local gh help commands. Neither commands nor outputs are persisted to disk.
    """

    BINDINGS = [Binding("escape", "close", "Back", priority=True)]
    DEFAULT_CSS = """
    GitHubPanel { background: $background; padding: 0 1; }
    GitHubPanel #gh-title { height: 2; text-style: bold; color: $accent; }
    GitHubPanel .gh-row { height: 3; }
    GitHubPanel .gh-row Input { width: 1fr; }
    GitHubPanel #gh-main { height: 1fr; }
    GitHubPanel #gh-catalog-pane { width: 33%; min-width: 25; border: round $primary; }
    GitHubPanel #gh-detail { width: 1fr; border: round $primary; }
    GitHubPanel #gh-tree { height: 1fr; }
    GitHubPanel #gh-command { height: 5; }
    GitHubPanel #gh-tabs { height: 1fr; }
    GitHubPanel #gh-help { height: 1fr; }
    GitHubPanel #gh-log { height: 1fr; }
    GitHubPanel #gh-status { height: 2; color: $text-muted; }
    GitHubPanel #gh-buttons { height: 6; layout: grid; grid-size: 4; }
    GitHubPanel Button { min-width: 10; width: 1fr; }
    GitHubPanel #gh-flag { width: 45%; }
    GitHubPanel #gh-timeout { width: 18; }
    """

    def __init__(self, repo_path: str | Path = ".", *, repo: str = "", standalone: bool = False):
        super().__init__()
        self.repo_path = Path(repo_path).expanduser().absolute()
        self.repo = repo
        self.standalone = standalone
        self.commands: list[catalog.Command] = []
        self.selected_command: catalog.Command | None = None
        self.runner: runner.CommandRunner | None = None
        self.busy = False
        self.last_result: runner.Result | None = None

    def compose(self) -> ComposeResult:
        exit_hint = "Escape to quit" if self.standalone else "Escape to return"
        yield Label(f"GitHub Explorer · {exit_hint}", id="gh-title")
        with Horizontal(classes="gh-row"):
            yield Input(str(self.repo_path), placeholder="Working directory", id="gh-cwd")
            yield Input(
                self.repo, placeholder="Repository override: OWNER/REPO (optional)", id="gh-repo"
            )
        with Horizontal(id="gh-main"):
            with Vertical(id="gh-catalog-pane"):
                yield Input(placeholder="Search every gh command…", id="gh-search")
                yield Tree("GitHub CLI", id="gh-tree")
            with Vertical(id="gh-detail"):
                yield Label("Command · edit arguments or enter any gh command")
                yield TextArea("gh repo view", id="gh-command")
                with Horizontal(classes="gh-row"):
                    yield Select([], prompt="Add a flag", id="gh-flag")
                    yield Input(placeholder="Flag value (one argument)", id="gh-value")
                    yield Button("Add flag", id="gh-add-flag")
                with Horizontal(classes="gh-row"):
                    yield Input(placeholder="Positional argument (one argument)", id="gh-arg")
                    yield Button("Add argument", id="gh-add-arg")
                    yield Input("300", placeholder="Timeout seconds", id="gh-timeout")
                with TabbedContent(id="gh-tabs"):
                    with TabPane("Command help", id="gh-help-tab"):
                        yield TextArea(
                            "Loading the installed gh command catalog…",
                            read_only=True,
                            id="gh-help",
                        )
                    with TabPane("Output", id="gh-output-tab"):
                        yield RichLog(
                            wrap=True, markup=False, highlight=False, max_lines=5000, id="gh-log"
                        )
        yield Static(
            "Select a command, add arguments, then Run or Terminal.", id="gh-status", markup=False
        )
        with Horizontal(id="gh-buttons"):
            yield Button("Run", id="gh-run", variant="primary")
            yield Button("Terminal", id="gh-terminal")
            yield Button("Stop", id="gh-stop", disabled=True)
            yield Button("Quit" if self.standalone else "Back", id="gh-close")
            yield Button("Fetch help", id="gh-fetch-help")
            yield Button("Reload catalog", id="gh-reload")
            yield Button("Copy output", id="gh-copy")
            yield Button("Clear output", id="gh-clear")

    def on_mount(self):
        self.load_commands()

    @work(thread=True, exclusive=True, group="gh-catalog")
    def load_commands(self):
        worker = get_current_worker()
        try:
            commands = catalog.load_catalog(self.repo_path)
        except Exception as exc:
            if not worker.is_cancelled:
                self.app.call_from_thread(self.catalog_failed, str(exc), worker)
        else:
            if not worker.is_cancelled:
                self.app.call_from_thread(self.loaded, commands, worker)

    def catalog_failed(self, message, worker):
        if self.is_mounted and not worker.is_cancelled:
            self.status(message)

    def loaded(self, commands, worker):
        # Cancelling a Textual thread worker does not stop its underlying thread.
        if not self.is_mounted or worker.is_cancelled:
            return
        self.commands = commands
        self.filter_commands()
        self.status(
            f"{len(commands)} commands from installed gh. Account and organization commands retain their normal scope."
        )

    def status(self, text):
        self.query_one("#gh-status", Static).update(text)

    @on(Input.Changed, "#gh-search")
    def filter_commands(self):
        query = self.query_one("#gh-search", Input).value.casefold()
        tree = self.query_one("#gh-tree", Tree)
        tree.clear()
        nodes = {(): tree.root}
        for command in self.commands:
            if query not in f"{command.name} {command.summary}".casefold():
                continue
            for depth in range(1, len(command.path) + 1):
                path = command.path[:depth]
                if path not in nodes:
                    nodes[path] = nodes[path[:-1]].add(Text(path[-1]), expand=bool(query))
            nodes[command.path].data = command
        tree.root.expand()

    @on(Tree.NodeSelected, "#gh-tree")
    def choose_command(self, event: Tree.NodeSelected):
        if not isinstance(event.node.data, catalog.Command):
            return
        command = self.selected_command = event.node.data
        self.query_one("#gh-command", TextArea).load_text(shlex.join(["gh", *command.path]))
        self.query_one("#gh-help", TextArea).load_text(command.help)
        self.query_one("#gh-flag", Select).set_options(
            [
                (f"{flag.name} {flag.value_type} — {flag.description}", index)
                for index, flag in enumerate(command.flags)
            ]
        )
        self.query_one("#gh-tabs", TabbedContent).active = "gh-help-tab"

    def append_arguments(self, *args):
        command = self.query_one("#gh-command", TextArea)
        command.load_text(command.text.rstrip() + " " + shlex.join(args))

    @on(Button.Pressed)
    def pressed(self, event: Button.Pressed):
        event.stop()
        action = event.button.id
        if action == "gh-close":
            self.action_close()
        elif action == "gh-stop":
            if self.runner:
                self.runner.cancel()
                self.status("Stopping command… Completed GitHub actions are not undone.")
        elif action == "gh-reload":
            if not self.busy:
                self.repo_path = (
                    Path(self.query_one("#gh-cwd", Input).value).expanduser().absolute()
                )
                self.load_commands()
        elif action == "gh-add-arg":
            value = self.query_one("#gh-arg", Input)
            if value.value:
                self.append_arguments(value.value)
                value.value = ""
        elif action == "gh-add-flag":
            choice = self.query_one("#gh-flag", Select).value
            if choice is not Select.BLANK and self.selected_command:
                flag = self.selected_command.flags[int(choice)]
                value = self.query_one("#gh-value", Input).value
                if flag.value_type and not value:
                    self.status(f"Enter a value for {flag.name}")
                else:
                    self.append_arguments(flag.name, *([value] if flag.value_type else []))
        elif action == "gh-fetch-help":
            if not self.busy:
                # Use only the catalog command path, not arbitrary entered arguments.
                if self.selected_command:
                    self.query_one("#gh-command", TextArea).load_text(
                        shlex.join(["gh", *self.selected_command.path, "--help"])
                    )
                    self.request_run(False)
        elif action in {"gh-run", "gh-terminal"}:
            self.request_run(action == "gh-terminal")
        elif action == "gh-copy":
            if self.last_result:
                self.app.copy_to_clipboard(self.last_result.output)
                self.status("Copied captured output to clipboard")
        elif action == "gh-clear":
            if not self.busy:
                self.query_one("#gh-log", RichLog).clear()
                self.last_result = None

    def request_run(self, interactive):
        if self.busy:
            self.status("A command is running. Stop it before starting another.")
            return
        try:
            invocation = runner.prepare(
                self.query_one("#gh-command", TextArea).text,
                self.query_one("#gh-cwd", Input).value,
                self.query_one("#gh-repo", Input).value,
            )
            timeout = float(self.query_one("#gh-timeout", Input).value)
            if not 0 < timeout <= 86400:
                raise ValueError("Timeout must be between 0 and 86400 seconds")
        except (ValueError, OSError) as exc:
            self.status(str(exc))
            return
        self.app.push_screen(
            CommandConfirm(invocation, interactive),
            lambda yes: self.start_command(invocation, interactive, timeout) if yes else None,
        )

    def start_command(self, invocation, interactive, timeout):
        if self.busy:
            return
        self.busy = True
        self.runner = runner.CommandRunner()
        self.last_result = None
        self.query_one("#gh-stop", Button).disabled = interactive
        self.query_one("#gh-run", Button).disabled = True
        self.query_one("#gh-terminal", Button).disabled = True
        self.query_one("#gh-tabs", TabbedContent).active = "gh-output-tab"
        self.query_one("#gh-log", RichLog).clear()
        self.write_output(invocation.preview)
        self.status("Running in terminal…" if interactive else "Running…")
        self.execute(invocation, interactive, timeout)

    def write_output(self, text):
        self.query_one("#gh-log", RichLog).write(Text(text))

    @work(thread=True, group="gh-execute")
    def execute(self, invocation, interactive, timeout):
        try:
            if interactive:
                with self.app.suspend():
                    result = runner.Result(
                        runner.run_interactive(invocation),
                        "Interactive terminal session; output was not captured.",
                    )
            else:
                result = self.runner.run(
                    invocation,
                    lambda text: self.app.call_from_thread(self.write_output, text),
                    timeout,
                )
        except Exception as exc:
            result = runner.Result(-1, str(exc))
        if self.is_mounted:
            self.app.call_from_thread(self.finished, result)

    def finished(self, result):
        self.last_result = result
        self.busy = False
        self.query_one("#gh-stop", Button).disabled = True
        self.query_one("#gh-run", Button).disabled = False
        self.query_one("#gh-terminal", Button).disabled = False
        suffix = " · cancelled" if result.cancelled else " · timed out" if result.timed_out else ""
        if result.truncated:
            suffix += " · captured output limited to 2 million characters"
        self.status(f"Exit {result.returncode}{suffix}")
        if result.returncode == -1:
            self.write_output(result.output)

    def action_close(self):
        if self.busy:
            self.status("Stop the running command before closing the panel")
        else:
            self.dismiss(self.last_result)

    def on_unmount(self):
        if self.runner:
            self.runner.cancel()
