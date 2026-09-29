# Contributor onboarding

1. Read [README](../README.md), [AGENTS.md](../AGENTS.md), and
   [architecture](ARCHITECTURE.md). Understand that executed `gh` commands may
   mutate repositories or accounts even though discovery only reads help.
2. Follow [installation](INSTALLATION.md), then run `uv sync --locked`.
3. Run `uv run pytest`, `uv run ruff check .`, and `uv build`.
4. Inspect `catalog.py` and its fixtures, then `runner.py` and its process tests.
   Read `panel.py` alongside `tests/test_panel.py` for confirmation and lifecycle.
5. Start `uv run github-explorer --cwd .`. Browse/search and inspect previews.
   Use only read-only operations for a live smoke test. Embedded Vim save tests
   use temporary fixture files; on a real project, open and :q without editing.
6. Make a small focused change using [development](DEVELOPMENT.md). Record the
   request and outcome in the versioned workflow logs; keep private data out.
7. Regenerate relevant metadata, rerun checks, review the diff, and submit a PR
   following [CONTRIBUTING.md](../CONTRIBUTING.md).

No repo-local agents, MCP credentials, database setup, production access, or
semantic-indexing service is required. Use [components](COMPONENTS.md) and the
[generated file map](codebase-overview.md) to find implementation entry points.
