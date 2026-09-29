"""Standalone host; the panel remains embeddable in another Textual App."""

from pathlib import Path

from textual.app import App

from .panel import GitHubPanel


class GitHubExplorer(App):
    TITLE = "GitHub Explorer"
    SUB_TITLE = "Your GitHub CLI, explored"

    def __init__(self, cwd: Path | str = ".", repo: str = ""):
        super().__init__()
        self.cwd = Path(cwd).expanduser().absolute()
        self.repo = repo

    def on_mount(self):
        self.push_screen(
            GitHubPanel(self.cwd, repo=self.repo, standalone=True),
            lambda result: self.exit(),
        )
