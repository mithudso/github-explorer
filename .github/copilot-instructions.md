## Default Execution Strategy

Read the affected files before editing. Decompose independent work when useful;
give each parallel worker clear ownership and preserve other workers' changes.
Complete files without placeholder omissions and continue through verification.
Never invent commands or paths. Run checks appropriate to each change set.
Follow the workflow log rule in [CLAUDE.md](../CLAUDE.md): keep `prompts.md` and
`memory.md` current, increment versions/deltas, and commit the task's changes.
Summarize changed files, validation, and any remaining gaps when done.

## Orientation

Read [AGENTS.md](../AGENTS.md), [README.md](../README.md),
[development](../docs/DEVELOPMENT.md), [architecture](../docs/ARCHITECTURE.md),
[testing](../docs/TESTING.md), and [security](../docs/SECURITY.md).

## Build, Test, and Validation Commands

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

No type-checker or development server is configured.

## High-level Architecture

`__main__.py` → `app.py` → `panel.py` → `catalog.py` / `runner.py` → installed `gh`.
Discovery invokes local help; execution requires a preview and confirmation.
There is no database, HTTP server, or MCP server.

## Key Conventions

1. Keep discovery, execution, reusable screen, and standalone host separate.
2. Keep public exports in `src/github_explorer/__init__.py`.
3. Never execute aliases or extensions during discovery.
4. Execute argv without a shell and preserve repository context previews.
5. Preserve cancellation, bounded capture, and captured-mode timeouts.
6. Do not persist command output or credentials.
7. Test with fixtures; live smoke operations must be read-only.
8. Preserve `LICENSE`, `NOTICE.md`, and unrelated worktree changes.
9. Regenerate metadata from its source instead of editing generated JSON.
10. Keep this public repository free of local state and private project data.
