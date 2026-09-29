import pytest

from github_explorer import runner


@pytest.fixture
def ui_repository(monkeypatch):
    """Keep every UI test off the network; individual tests replace these fixtures."""
    monkeypatch.setattr(runner, "executable", lambda: "/fixture/gh")
    monkeypatch.setattr(
        runner, "repository_info",
        lambda context, executor: runner.Repository(
            context, "owner/repository", "github.com", "main",
            {"description": "Fixture description", "has_issues": True, "topics": ["python"]},
        ),
    )
    monkeypatch.setattr(runner, "repository_files", lambda repository, executor: [])
    def no_checkout(cwd, executor):
        raise ValueError("Fixture has no local checkout")
    monkeypatch.setattr(runner, "workspace_status", no_checkout)
    monkeypatch.setattr(runner, "repository_activity", lambda repository, executor: ([], []))
