"""Reusable GitHub control screen with an embedded Vim terminal."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
    Tabs,
    TextArea,
    Tree,
)
from textual.worker import get_current_worker
from textual_tty import Terminal

from . import catalog, runner

ARROW_BINDINGS = [
    Binding(key, f"navigate('{key}')", show=False, priority=True)
    for key in ("up", "down", "left", "right")
]


class ArrowNavigation:
    """Directional focus, with native text, dropdown and tab navigation retained."""

    def check_action(self, action, parameters):
        if isinstance(self.focused, VimEditor) and action in {
            "navigate", "close", "quick_command", "toggle_actions",
        }:
            return False
        if action == "navigate":
            focused = self.focused
            direction = parameters[0]
            if isinstance(focused, TextArea):
                if not focused.read_only:
                    return False
                row, column = focused.cursor_location
                last_row = focused.document.line_count - 1
                at_edge = {
                    "up": row == 0,
                    "down": row == last_row,
                    "left": (row, column) == (0, 0),
                    "right": (row, column) == (last_row, len(focused.document.get_line(last_row))),
                }
                if not at_edge[direction]:
                    return False
            if isinstance(focused, RichLog):
                can_scroll = {
                    "up": focused.scroll_y > 0,
                    "down": focused.scroll_y < focused.max_scroll_y,
                    "left": focused.scroll_x > 0,
                    "right": focused.scroll_x < focused.max_scroll_x,
                }
                if can_scroll[direction]:
                    return False
            if isinstance(focused, (Input, Tabs)) and direction in {"left", "right"}:
                return False
            if focused:
                for widget in focused.ancestors_with_self:
                    if isinstance(widget, Select):
                        if widget.expanded or direction in {"up", "down"}:
                            return False
        return super().check_action(action, parameters)

    def action_navigate(self, direction):
        focused = self.focused
        if isinstance(focused, Tree):
            node = focused.cursor_node
            if node:
                if direction in {"down", "right"} and node.children and not node.is_expanded:
                    node.expand()
                    return
                if direction == "down" and focused.cursor_line < focused.last_line:
                    focused.action_cursor_down()
                    return
                if direction == "up" and focused.cursor_line > 0:
                    focused.action_cursor_up()
                    return
                if direction == "right" and node.children:
                    focused.move_cursor(node.children[0])
                    return
                if direction == "left":
                    if node.children and node.is_expanded:
                        node.collapse()
                        return
                    if node.parent:
                        focused.move_cursor(node.parent)
                        return
        self.focus_in_direction(direction)

    def focus_in_direction(self, direction):
        focused = self.focused
        if focused is None:
            self.focus_next()
            return
        origin = focused.region
        horizontal = direction in {"left", "right"}
        forward = direction in {"right", "down"}
        candidates = []
        for widget in self.focus_chain:
            if widget is focused or not widget.region:
                continue
            region = widget.region
            if horizontal:
                distance = region.x - origin.right if forward else origin.x - region.right
                overlap = min(origin.bottom, region.bottom) - max(origin.y, region.y)
                offset = abs(region.center[1] - origin.center[1])
            else:
                distance = region.y - origin.bottom if forward else origin.y - region.bottom
                overlap = min(origin.right, region.right) - max(origin.x, region.x)
                offset = abs(region.center[0] - origin.center[0])
            if distance >= 0:
                candidates.append(((overlap <= 0, distance, offset), widget))
        if candidates:
            min(candidates, key=lambda candidate: candidate[0])[1].focus()


class VimEditor(Terminal):
    """Actual Vim in a PTY; the application never copies a remote blob to disk."""

    class Closed(Message):
        def __init__(self, editor, exit_code):
            self.editor, self.exit_code = editor, exit_code
            super().__init__()

    def render_line(self, y):
        # Resizing may expose a blank PTY row before the emulator resizes.
        # Textual's monochrome filter requires a Style even on blank segments.
        return super().render_line(y).apply_style(self.rich_style)

    async def on_mount(self, event):
        # Textual dispatches mount to each class in the MRO. Terminal's handler
        # already calls its base; prevent a second PTY/process from being started.
        event.prevent_default()
        await super().on_mount()
        if self.board.process is None:
            self.post_message(self.Closed(self, -1))

    def ex(self, command):
        self.board.display.input("\x1b\x1b:" + command + "\r")
        self.focus()

    def open_file(self, path):
        self.ex("execute 'confirm edit ' . fnameescape(" + json.dumps(str(path), ensure_ascii=False) + ")")

    @on(Terminal.ProcessExited)
    def exited(self, event):
        event.stop()
        self.post_message(self.Closed(self, event.exit_code))


class RepositoryStatus(ArrowNavigation, ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close"), *ARROW_BINDINGS]
    DEFAULT_CSS = """
    RepositoryStatus { align: center middle; }
    RepositoryStatus > Vertical { width: 100; max-width: 95%; height: 80%;
        background: $surface; border: round $primary; padding: 1 2; }
    RepositoryStatus TextArea { height: 1fr; }
    """

    def __init__(self, text):
        super().__init__()
        self.text = text

    def compose(self):
        with Vertical():
            yield Label("Repository status")
            yield TextArea(self.text, read_only=True)
            yield Button("Close", id="status-close")

    @on(Button.Pressed)
    def close(self, event):
        event.stop()
        self.dismiss()


class CommandConfirm(ArrowNavigation, ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel"), *ARROW_BINDINGS]
    DEFAULT_CSS = """
    CommandConfirm { align: center middle; }
    CommandConfirm > Vertical { width: 100; max-width: 95%; height: auto;
        max-height: 90%; border: round $primary; padding: 1 2; background: $surface; }
    CommandConfirm TextArea { height: 12; }
    CommandConfirm Horizontal { height: 3; }
    """

    def __init__(self, invocation: runner.Invocation, interactive: bool, hint: str = ""):
        super().__init__()
        self.invocation, self.interactive = invocation, interactive
        self.hint = hint

    def compose(self) -> ComposeResult:
        with Vertical():
            name = "Git" if self.invocation.program == "git" else "GitHub"
            yield Label(f"Run {name} command{' in terminal' if self.interactive else ''}?")
            if self.hint:
                yield Static(self.hint, markup=False)
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


class RepoSettings(ArrowNavigation, ModalScreen):
    """Edit CLI-discovered options against a repository identity frozen on load."""

    BINDINGS = [("escape", "cancel", "Close"), *ARROW_BINDINGS]
    DEFAULT_CSS = """
    RepoSettings { align: center middle; }
    RepoSettings > Vertical { width: 110; max-width: 95%; height: 90%;
        border: round $primary; padding: 1 2; background: $surface; }
    RepoSettings #settings-status { height: auto; max-height: 6; margin-bottom: 1; }
    RepoSettings #settings-fields { height: 1fr; }
    RepoSettings .setting { height: auto; margin-bottom: 1; }
    RepoSettings .setting Label { height: auto; }
    RepoSettings .setting Horizontal { height: 3; }
    RepoSettings Checkbox { width: 14; }
    RepoSettings Input, RepoSettings Select { width: 1fr; }
    RepoSettings #settings-buttons { height: 3; }
    """

    def __init__(self, context: runner.Invocation):
        super().__init__()
        self.context = context
        self.executor = runner.CommandRunner()
        self.repository = None
        self.flags = ()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Repository settings", id="settings-title", markup=False)
            yield Static("Loading current settings…", id="settings-status", markup=False)
            yield VerticalScroll(id="settings-fields")
            with Horizontal(id="settings-buttons"):
                yield Button("Review changes", id="settings-review", variant="primary", disabled=True)
                yield Button("Close", id="settings-close")

    def on_mount(self):
        self.load_settings()

    @work(thread=True, exclusive=True)
    def load_settings(self):
        worker = get_current_worker()
        try:
            flags = catalog.repository_settings(self.context.cwd)
            repository = runner.repository_info(self.context, self.executor)
        except Exception as exc:
            if not worker.is_cancelled:
                self.app.call_from_thread(self.load_failed, str(exc))
        else:
            if not worker.is_cancelled:
                self.app.call_from_thread(self.show_settings, repository, flags)

    def load_failed(self, message):
        if self.is_mounted:
            self.query_one("#settings-status", Static).update(message)

    async def show_settings(self, repository, flags):
        if not self.is_mounted:
            return
        self.repository, self.flags = repository, flags
        self.query_one("#settings-title", Label).update(Text(f"Repository settings · {repository.target}"))
        topics = ", ".join(repository.settings.get("topics", [])) or "none"
        self.query_one("#settings-status", Static).update(
            f"Check Change for each option to apply. Unknown values are not guessed.\n"
            f"Current topics: {topics}. Topic fields accept comma-separated names."
        )
        rows = []
        for index, flag in enumerate(flags):
            value = catalog.setting_value(flag, repository.settings)
            if flag.value_type:
                editor = Input("" if value is None else str(value), id=f"setting-value-{index}")
            else:
                editor = Select(
                    [("Enabled / true", "true"), ("Disabled / false", "false")],
                    value=Select.NULL if value is None else str(value).lower(),
                    prompt="Choose a value", id=f"setting-value-{index}",
                )
            current = "unknown / action option" if value is None else str(value)
            if value == "":
                current = "(empty)"
            rows.append(Vertical(
                Label(Text(f"{flag.name} · {flag.description}")),
                Label(Text(f"Current: {current}")),
                Horizontal(Checkbox("Change", id=f"setting-change-{index}"), editor),
                classes="setting",
            ))
        await self.query_one("#settings-fields", VerticalScroll).mount(*rows)
        self.query_one("#settings-review", Button).disabled = not bool(flags)

    @on(Button.Pressed)
    def pressed(self, event: Button.Pressed):
        event.stop()
        if event.button.id == "settings-close":
            self.action_cancel()
        elif event.button.id == "settings-review" and self.repository:
            try:
                changes = {}
                for index, flag in enumerate(self.flags):
                    if self.query_one(f"#setting-change-{index}", Checkbox).value:
                        value = self.query_one(f"#setting-value-{index}").value
                        if value is Select.NULL:
                            raise ValueError(f"Choose a value for {flag.name}")
                        changes[flag.name] = value
                args = catalog.settings_arguments(self.flags, changes)
                command = shlex.join(["gh", "repo", "edit", f"https://{self.repository.target}", *args])
                invocation = runner.prepare(command, self.context.cwd, self.repository.target)
            except (ValueError, OSError) as exc:
                self.load_failed(str(exc))
                return
            def confirmed(yes):
                if yes:
                    self.dismiss(invocation)

            self.app.push_screen(CommandConfirm(invocation, False), confirmed)

    def action_cancel(self):
        self.executor.cancel()
        self.dismiss(None)

    def on_unmount(self):
        self.executor.cancel()


class GitHubPanel(ArrowNavigation, Screen):
    """Push onto any Textual 8 App; Escape returns to the host TUI.

    repo_path is the actual working directory used for gh and git. repo is an optional
    OWNER/REPO or HOST/OWNER/REPO GH_REPO override. Entry reads local help and
    remote repository files. Neither commands nor outputs are persisted to disk.
    """

    BINDINGS = [
        Binding("escape", "close", "Back", priority=True),
        Binding("ctrl+b", "toggle_actions", "Hide/show actions", priority=True),
        Binding("ctrl+backslash", "focus_files", "File list", priority=True),
        Binding("ctrl+s", "save_file", "Save file", priority=True),
        *ARROW_BINDINGS,
        *(Binding(action.key, f"quick_command('{action.id}')", action.label, priority=True)
          for action in catalog.QUICK_ACTIONS),
    ]
    DEFAULT_CSS = """
    GitHubPanel { background: $background; padding: 0 1; }
    GitHubPanel #gh-title { height: 2; text-style: bold; color: $accent; }
    GitHubPanel .gh-row { height: 3; }
    GitHubPanel .gh-row Input { width: 1fr; }
    GitHubPanel #gh-main { height: 1fr; }
    GitHubPanel #gh-catalog-pane { width: 33%; min-width: 25; border: round $primary; }
    GitHubPanel #gh-detail { width: 1fr; border: round $primary; }
    GitHubPanel #gh-tree { height: 1fr; }
    GitHubPanel #gh-files { height: 2fr; }
    GitHubPanel #gh-file-status { height: auto; max-height: 4; color: $text-muted; }
    GitHubPanel #gh-file-preview { height: 1fr; }
    GitHubPanel #gh-vim { height: 1fr; }
    GitHubPanel #gh-editor-buttons { height: 1; }
    GitHubPanel #gh-editor-buttons Button { height: 1; }
    GitHubPanel #gh-command-controls { height: auto; }
    GitHubPanel #gh-persistent-status { height: 2; background: $boost; }
    GitHubPanel #gh-repository-status { height: 2; width: 1fr; }
    GitHubPanel #gh-persistent-status Button { height: 1; width: 18; min-width: 12; }
    GitHubPanel #gh-file-title { height: auto; max-height: 3; }
    GitHubPanel #gh-command { height: 5; }
    GitHubPanel #gh-tabs { height: 1fr; }
    GitHubPanel #gh-help { height: 1fr; }
    GitHubPanel #gh-log { height: 1fr; }
    GitHubPanel #gh-status { height: 2; color: $text-muted; }
    GitHubPanel #gh-buttons { height: 6; layout: grid; grid-size: 4; }
    GitHubPanel #gh-quick-title { height: 1; color: $accent; }
    GitHubPanel #gh-quick-buttons { height: 2; layout: grid; grid-size: 6;
        grid-rows: 1; grid-gutter: 0 1; }
    GitHubPanel #gh-quick-buttons Button { height: 1; min-width: 0; }
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
        self.repository: runner.Repository | None = None
        self.files: list[dict] = []
        self.readers: dict[str, runner.CommandRunner] = {}
        self.refresh_after_run = False
        self.workspace = None
        self.local_status = None
        self.local_error = "Loading local checkout…"
        self.open_prs = None
        self.remote_branches = None
        self.activity_error = "Loading GitHub status…"
        self.editor = None
        self.actions_visible = True
        self._status_worker = None
        self._activity_worker = None

    def compose(self) -> ComposeResult:
        exit_hint = "Escape to quit" if self.standalone else "Escape to return"
        yield Label(f"GitHub Explorer · {exit_hint}", id="gh-title")
        with Horizontal(classes="gh-row"):
            yield Input(str(self.repo_path), placeholder="Working directory · Enter to load", id="gh-cwd")
            yield Input(
                self.repo, placeholder="Repository: [HOST/]OWNER/REPO · Enter to load", id="gh-repo"
            )
        with Horizontal(id="gh-main"):
            with Vertical(id="gh-catalog-pane"):
                with Horizontal(classes="gh-row"):
                    yield Button("Refresh files", id="gh-refresh-files")
                    yield Button("Repo settings", id="gh-settings")
                yield Input(placeholder="Find a repository file…", id="gh-file-search")
                yield Static("Loading repository files…", id="gh-file-status", markup=False)
                yield Tree("Repository files", id="gh-files")
                yield Input(placeholder="Search gh and Git commands…", id="gh-search")
                yield Tree("Commands · gh + git", id="gh-tree")
            with Vertical(id="gh-detail"):
                with Vertical(id="gh-command-controls"):
                    yield Label("Command · enter gh or git commands and arguments")
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
                    with TabPane("Repository files", id="gh-files-tab"):
                        yield Static("Select a file to preview it.", id="gh-file-title", markup=False)
                        with Horizontal(id="gh-editor-buttons"):
                            yield Button("Save :w", id="gh-save-file", compact=True, disabled=True)
                            yield Button("Close :q", id="gh-close-editor", compact=True, disabled=True)
                        yield TextArea("", read_only=True, id="gh-file-preview")
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
        yield Static("Common actions · buttons and F1–F12 open a confirmation", id="gh-quick-title")
        with Horizontal(id="gh-quick-buttons"):
            for action in catalog.QUICK_ACTIONS:
                yield Button(
                    f"{action.key.upper()} {action.label}", id=f"quick-{action.id}",
                    compact=True, tooltip=f"{' '.join(action.argv)} — {action.description}",
                )

        with Horizontal(id="gh-persistent-status"):
            yield Static("Branch: loading · Changed: …\nPRs: … · Other branches: …", id="gh-repository-status", markup=False)
            yield Button("Status / refresh", id="gh-status-details", compact=True)
            yield Button("Hide actions", id="gh-toggle-actions", compact=True)

    def on_mount(self):
        self.set_interval(2, self.refresh_local_status)
        self.set_interval(60, self.refresh_activity)
        self.load_commands()
        self.refresh_files()
        self.query_one("#gh-files", Tree).focus()

    def on_resize(self, event):
        if not self.is_mounted:
            return
        columns = 6 if event.size.width >= 110 else 4 if event.size.width >= 76 else 3
        bar = self.query_one("#gh-quick-buttons", Horizontal)
        bar.styles.grid_size_columns = columns
        bar.styles.height = (len(catalog.QUICK_ACTIONS) + columns - 1) // columns

    def current_context(self):
        return runner.prepare(
            "gh repo view", self.query_one("#gh-cwd", Input).value,
            self.query_one("#gh-repo", Input).value,
        )

    def context_matches(self, context):
        try:
            current = self.current_context()
            return current.cwd == context.cwd and current.repo == context.repo
        except (ValueError, OSError):
            return False

    def new_reader(self, group):
        if group in self.readers:
            self.readers[group].cancel()
        executor = self.readers[group] = runner.CommandRunner()
        return executor

    @on(Input.Submitted, "#gh-cwd")
    @on(Input.Submitted, "#gh-repo")
    def refresh_files(self):
        if self.editor:
            self.status("Close Vim with :wq or :q before changing repository context or refreshing files.")
            return
        for group in ("preview", "activity", "local-status"):
            if group in self.readers:
                self.readers[group].cancel()
        for worker in (self._activity_worker, self._status_worker):
            if worker:
                worker.cancel()
        self._activity_worker = self._status_worker = None
        self.repository = None
        self.workspace = None
        self.open_prs = self.remote_branches = None
        self.activity_error = "Loading GitHub status…"
        self.files = []
        self.filter_files()
        self.render_repository_status()
        self.refresh_local_status()
        self.query_one("#gh-file-preview", TextArea).load_text("")
        self.query_one("#gh-file-title", Static).update("Select a file to preview it.")
        try:
            context = self.current_context()
        except (ValueError, OSError) as exc:
            self.query_one("#gh-file-status", Static).update(str(exc))
            return
        self.query_one("#gh-file-status", Static).update("Loading GitHub default-branch files…")
        self.load_files(context, self.new_reader("files"))

    @work(thread=True, exclusive=True, group="gh-files")
    def load_files(self, context, executor):
        worker = get_current_worker()
        workspace = None
        try:
            repository = runner.repository_info(context, executor)
            try:
                candidate = runner.workspace_status(context.cwd, executor)
                if runner.workspace_matches(repository, candidate, executor):
                    workspace = candidate
            except (ValueError, OSError):
                pass
            if workspace:
                files = runner.workspace_files(workspace, executor)
                message = f"Local checkout · {workspace.branch} · {len(files)} files"
            else:
                files = runner.repository_files(repository, executor)
                message = f"GitHub · {repository.branch or 'empty'} · {len(files)} files · read-only"
        except Exception as exc:
            repository, files, message = None, [], str(exc)
        if not worker.is_cancelled and not executor.cancelled.is_set():
            self.app.call_from_thread(self.files_loaded, context, repository, files, message, worker, workspace)

    def files_loaded(self, context, repository, files, message, worker, workspace=None):
        if not self.is_mounted or worker.is_cancelled or not self.context_matches(context):
            return
        self.repository, self.files = repository, files
        self.workspace = workspace
        self.query_one("#gh-file-status", Static).update(message)
        self.filter_files()
        self.refresh_activity()

    @on(Input.Changed, "#gh-file-search")
    def filter_files(self):
        query = self.query_one("#gh-file-search", Input).value.casefold()
        tree = self.query_one("#gh-files", Tree)
        tree.clear()
        nodes = {(): tree.root}
        for entry in self.files:
            if query not in entry["path"].casefold():
                continue
            parts = tuple(entry["path"].split("/"))
            for depth in range(1, len(parts)):
                prefix = parts[:depth]
                if prefix not in nodes:
                    nodes[prefix] = nodes[prefix[:-1]].add(Text(prefix[-1]), expand=bool(query))
            nodes[parts[:-1]].add_leaf(Text(parts[-1]), data=entry)
        tree.root.expand()

    @on(Tree.NodeSelected, "#gh-files")
    async def choose_file(self, event: Tree.NodeSelected):
        if not isinstance(event.node.data, dict) or not self.repository:
            return
        if not self.context_matches(self.repository.context):
            self.status("Repository context changed. Refresh files first.")
            return
        entry = event.node.data
        self.query_one("#gh-tabs", TabbedContent).active = "gh-files-tab"
        if entry["type"] == "local" and self.workspace:
            try:
                path = runner.editable_file(self.workspace, entry["path"])
                if self.editor:
                    self.editor.open_file(path)
                else:
                    editor = VimEditor(command=runner.vim_command(self.workspace, path), id="gh-vim")
                    self.editor = editor
                    for selector in ("#gh-cwd", "#gh-repo", "#gh-refresh-files", "#gh-settings"):
                        self.query_one(selector).disabled = True
                    self.query_one("#gh-command-controls").display = False
                    self.query_one("#gh-file-preview").display = False
                    await self.query_one("#gh-files-tab", TabPane).mount(editor)
                    editor.focus()
                self.query_one("#gh-file-title", Static).update(
                    "Vim · :w saves locally · :q closes · Ctrl+\\ returns to files"
                )
                self.query_one("#gh-save-file", Button).disabled = False
                self.query_one("#gh-close-editor", Button).disabled = False
            except (OSError, ValueError) as exc:
                self.status(str(exc))
            return
        self.query_one("#gh-file-title", Static).update(
            entry["path"] + " · read-only GitHub preview; select a matching checkout to edit"
        )
        self.query_one("#gh-file-preview", TextArea).load_text("Loading file…")
        self.load_file(self.repository, entry, self.new_reader("preview"))

    @work(thread=True, exclusive=True, group="gh-file-preview")
    def load_file(self, repository, entry, executor):
        worker = get_current_worker()
        try:
            text = runner.repository_file_text(repository, entry, executor)
        except Exception as exc:
            text = str(exc)
        if not worker.is_cancelled and not executor.cancelled.is_set():
            self.app.call_from_thread(self.file_loaded, repository, text, worker, executor)

    def file_loaded(self, repository, text, worker, executor):
        if (self.is_mounted and not worker.is_cancelled and not executor.cancelled.is_set()
                and self.repository is repository and self.context_matches(repository.context)):
            self.query_one("#gh-file-preview", TextArea).load_text(text)

    @on(VimEditor.Closed)
    async def editor_closed(self, event):
        event.stop()
        if event.editor is not self.editor:
            return
        self.editor = None
        for selector in ("#gh-cwd", "#gh-repo", "#gh-refresh-files", "#gh-settings"):
            self.query_one(selector).disabled = False
        await event.editor.remove()
        self.query_one("#gh-command-controls").display = True
        self.query_one("#gh-file-preview").display = True
        self.query_one("#gh-save-file", Button).disabled = True
        self.query_one("#gh-close-editor", Button).disabled = True
        self.status(f"Vim exited ({event.exit_code}); saved files remain in the local checkout.")
        self.refresh_files()
        self.refresh_local_status()
        self.action_focus_files()

    def action_save_file(self):
        if self.editor:
            self.editor.ex("write")
            self.status("Save requested in Vim; check its message for success or write errors.")
            self.set_timer(0.3, self.refresh_local_status)

    def action_focus_files(self):
        self.query_one("#gh-files", Tree).focus()

    def action_toggle_actions(self):
        self.actions_visible = not self.actions_visible
        for selector in ("#gh-buttons", "#gh-quick-title", "#gh-quick-buttons"):
            self.query_one(selector).display = self.actions_visible
        self.query_one("#gh-toggle-actions", Button).label = (
            "Hide actions" if self.actions_visible else "Show actions"
        )

    def refresh_local_status(self):
        if self._status_worker and self._status_worker.is_running:
            return
        cwd = self.query_one("#gh-cwd", Input).value
        self._status_worker = self.read_local_status(cwd, self.new_reader("local-status"))

    @work(thread=True, exclusive=True, group="gh-local-status")
    def read_local_status(self, cwd, executor):
        try:
            state = runner.workspace_status(Path(cwd).expanduser().resolve(), executor)
            error = ""
        except Exception as exc:
            state, error = None, str(exc)
        if not get_current_worker().is_cancelled:
            self.app.call_from_thread(self.local_status_loaded, cwd, state, error)

    def local_status_loaded(self, cwd, state, error):
        if not self.is_mounted or self.query_one("#gh-cwd", Input).value != cwd:
            return
        previous = self.local_status
        self.local_status, self.local_error = state, error
        self.render_repository_status()
        if (state and previous and state.branch != previous.branch and not self.editor):
            self.refresh_files()

    def refresh_activity(self):
        if not self.repository or not self.context_matches(self.repository.context):
            return
        if self._activity_worker and self._activity_worker.is_running:
            return
        self._activity_worker = self.read_activity(self.repository, self.new_reader("activity"))

    @work(thread=True, exclusive=True, group="gh-activity")
    def read_activity(self, repository, executor):
        try:
            prs, branches = runner.repository_activity(repository, executor)
            error = ""
        except Exception as exc:
            prs, branches, error = None, None, str(exc)
        if not get_current_worker().is_cancelled:
            self.app.call_from_thread(self.activity_loaded, repository, prs, branches, error)

    def activity_loaded(self, repository, prs, branches, error):
        if (self.is_mounted and self.repository is repository
                and self.context_matches(repository.context)):
            self.open_prs, self.remote_branches, self.activity_error = prs, branches, error
            self.render_repository_status()

    def repository_status_text(self):
        state = self.local_status
        branch = state.branch if state else "unavailable"
        changed = str(state.changed) if state else "unknown"
        names = set(self.remote_branches or [])
        if state and self.workspace:
            names.update(state.branches)
            names.discard(branch)
        others = ", ".join(sorted(names)) or "none"
        prs = self.open_prs
        numbers = ", ".join(f"#{pr['number']}" for pr in (prs or [])) or "none"
        pr_summary = "unknown" if prs is None else f"{len(prs)} ({numbers})"
        branch_summary = "unknown" if self.remote_branches is None else f"{len(names)} ({others})"
        summary = f"Branch: {branch} · Changed: {changed}\nPRs: {pr_summary} · Other branches: {branch_summary}"
        details = summary + f"\n\nLocal checkout: {state.root if state else 'unavailable'}"
        details += f"\nGitHub repository: {self.repository.target if self.repository else 'unavailable'}"
        details += "\n\nChanged counts include staged, unstaged, untracked and conflicted files once."
        details += "\nUnsaved Vim buffers are marked in Vim; the Git count updates after saving."
        details += "\n\n" + "\n".join(f"#{pr['number']} {pr['title']}\n{pr['url']}" for pr in (prs or []))
        if self.local_error:
            details += f"\n\nLocal status: {self.local_error}"
        if self.activity_error:
            details += f"\n\nGitHub status: {self.activity_error}"
        return summary, details

    def render_repository_status(self):
        summary, details = self.repository_status_text()
        widget = self.query_one("#gh-repository-status", Static)
        widget.update(summary)
        widget.tooltip = details
        if isinstance(self.app.screen, RepositoryStatus):
            view = self.app.screen.query_one(TextArea)
            if view.text != details:
                view.load_text(details)

    def settings_confirmed(self, invocation):
        if invocation:
            self.refresh_after_run = True
            self.start_command(invocation, False, 300)

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
            f"{len(commands)} gh commands plus local Git shortcuts. F1–F12: common actions."
        )

    def status(self, text):
        self.query_one("#gh-status", Static).update(text)

    @on(Input.Changed, "#gh-search")
    def filter_commands(self):
        query = self.query_one("#gh-search", Input).value.casefold()
        tree = self.query_one("#gh-tree", Tree)
        tree.clear()
        nodes = {("gh", ()): tree.root}
        for command in [*self.commands, *catalog.git_commands()]:
            if query not in f"{command.program} {command.name} {command.summary}".casefold():
                continue
            program = command.program
            if (program, ()) not in nodes:
                nodes[(program, ())] = tree.root.add(Text("Git · local checkout"), expand=bool(query))
            for depth in range(1, len(command.path) + 1):
                path = command.path[:depth]
                if (program, path) not in nodes:
                    nodes[(program, path)] = nodes[(program, path[:-1])].add(Text(path[-1]), expand=bool(query))
            nodes[(program, command.path)].data = command
        tree.root.expand()

    @on(Tree.NodeSelected, "#gh-tree")
    def choose_command(self, event: Tree.NodeSelected):
        if not isinstance(event.node.data, catalog.Command):
            return
        self.show_command(event.node.data)

    def show_command(self, command):
        self.selected_command = command
        self.query_one("#gh-command", TextArea).load_text(
            shlex.join([command.program, *command.path, *command.default_args])
        )
        self.query_one("#gh-help", TextArea).load_text(command.help)
        self.query_one("#gh-flag", Select).set_options(
            [
                (f"{flag.name} {flag.value_type} — {flag.description}", index)
                for index, flag in enumerate(command.flags)
            ]
        )
        self.query_one("#gh-tabs", TabbedContent).active = "gh-help-tab"

    def action_quick_command(self, action_id: str):
        if self.app.screen is not self:
            return
        if self.editor:
            self.status("Close Vim with :wq or :q before running repository commands.")
            return
        if self.busy:
            self.status("A command is running. Stop it before starting another.")
            return
        action = next((item for item in catalog.QUICK_ACTIONS if item.id == action_id), None)
        if action is None:
            return
        command = next((item for item in [*self.commands, *catalog.git_commands()]
                        if item.program == action.argv[0]
                        and item.path == action.argv[1:1 + len(item.path)]
                        and len(item.path) == (1 if item.program == "git" else 2)), None)
        if command:
            self.show_command(command)
        else:
            self.show_command(catalog.Command(
                action.argv[1:], action.description, action.description, program=action.argv[0],
            ))
        self.query_one("#gh-command", TextArea).load_text(shlex.join(action.argv))
        self.request_run(action.interactive, hint=action.description)

    def append_arguments(self, *args):
        command = self.query_one("#gh-command", TextArea)
        command.load_text(command.text.rstrip() + " " + shlex.join(args))

    @on(Button.Pressed)
    def pressed(self, event: Button.Pressed):
        event.stop()
        action = event.button.id
        if action == "gh-toggle-actions":
            self.action_toggle_actions()
        elif action == "gh-status-details":
            self.refresh_local_status()
            self.refresh_activity()
            self.app.push_screen(RepositoryStatus(self.repository_status_text()[1]))
        elif action == "gh-save-file":
            self.action_save_file()
        elif action == "gh-close-editor":
            if self.editor:
                self.editor.ex("confirm quit")
        elif action == "gh-close":
            self.action_close()
        elif action and action.startswith("quick-"):
            self.action_quick_command(action.removeprefix("quick-"))
        elif action == "gh-refresh-files":
            self.refresh_files()
        elif action == "gh-settings":
            if self.busy:
                self.status("Wait for the running command before editing settings.")
                return
            try:
                context = self.current_context()
            except (ValueError, OSError) as exc:
                self.status(str(exc))
                return
            self.app.push_screen(RepoSettings(context), self.settings_confirmed)
        elif action == "gh-stop":
            if self.runner:
                self.runner.cancel()
                self.status("Stopping command… Completed actions are not undone.")
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
            if choice is not Select.NULL and self.selected_command:
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
                        shlex.join([
                            self.selected_command.program, *self.selected_command.path,
                            "-h" if self.selected_command.program == "git" else "--help",
                        ])
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

    def request_run(self, interactive, hint=""):
        if self.editor:
            self.status("Close Vim with :wq or :q before running repository commands.")
            return
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
            CommandConfirm(invocation, interactive, hint),
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
        for button in self.query("#gh-quick-buttons Button"):
            button.disabled = True
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
        for button in self.query("#gh-quick-buttons Button"):
            button.disabled = False
        suffix = " · cancelled" if result.cancelled else " · timed out" if result.timed_out else ""
        if result.truncated:
            suffix += " · captured output limited to 2 million characters"
        self.status(f"Exit {result.returncode}{suffix}")
        self.refresh_local_status()
        self.refresh_activity()
        if result.returncode == -1:
            self.write_output(result.output)
        if self.refresh_after_run:
            self.refresh_after_run = False
            self.refresh_files()

    def action_close(self):
        if self.editor:
            self.status("Close Vim with :wq or :q first; Vim will protect unsaved changes.")
            self.query_one("#gh-tabs", TabbedContent).active = "gh-files-tab"
            self.editor.focus()
        elif self.busy:
            self.status("Stop the running command before closing the panel")
        else:
            self.dismiss(self.last_result)

    def on_unmount(self):
        if self.runner:
            self.runner.cancel()
        for executor in self.readers.values():
            executor.cancel()
