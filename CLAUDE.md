# GitHub Explorer contributor instructions

## Repository shape

This is one Python package. `src/github_explorer/` contains the CLI and Textual
screens. `tests/` contains fixture-based pytest tests. `scripts/` maintains docs
and workflow logs. `docs/` contains architecture, operations, and generated indexes.
Read [AGENTS.md](AGENTS.md), [README.md](README.md), then
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Commands

Run from the repository root:

```sh
uv sync --locked
uv run github-explorer --cwd .
uv run pytest
uv run pytest tests/test_runner.py
uv run ruff check .
uv build
uv run python scripts/generate_ops_registry_doc.py --check
uv run python scripts/check_doc_indexes.py
```

The app requires `gh` on PATH. Fixture tests do not require GitHub authentication.
There is no separate type-checker or service to start.

## Runtime architecture

`__main__.py` parses CLI options, `app.py` hosts `GitHubPanel` from `panel.py`,
`catalog.py` reads local `gh` help, and `runner.py` executes confirmed argv.
The panel supports embedding in another Textual 8 app. No server, database, or
background service runs. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Key conventions

- Keep discovery in `catalog.py`, execution in `runner.py`, UI in `panel.py`, and
  standalone hosting in `app.py`. Keep public exports in `__init__.py`.
- Discover using local help only. Never run aliases/extensions during loading.
- Execute argv without a shell; preserve confirmation and exact context previews.
- Preserve bounded capture, cancellation, and captured-mode timeouts.
- Keep terminal execution explicit; it may perform account-wide or local actions.
- Do not persist command output, argv, credentials, or private project data.
- Use fixture commands in tests. Live smoke tests must be read-only.
- Retain `LICENSE` and `NOTICE.md`; this is a public repository.
- Preserve unrelated dirty work; stage only the files belonging to the task.
- Regenerate derived docs after changing their source; do not hand-edit indexes.

## MCP servers

No repo-local MCP servers are required. `.mcp.json` and `.vscode/mcp.json` contain
empty server maps. User-level tools are independent of the application.

## Workflow log rule

Append every user request to `prompts.md` with an incremented version and delta.
Keep `memory.md` current with the task, completed work, changed files, validation,
and remaining steps. Use the existing versioned format. Keep public logs free of
credentials and private source-project data. Increment the release version in
`pyproject.toml`, `src/github_explorer/__init__.py`, and the lockfile when appropriate;
update `CHANGELOG.md`. Commit the task's changes after verification. Use
`scripts/rotate_workflow_logs.py` to archive oversized workflow logs.
