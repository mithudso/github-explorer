# GitHub Explorer

Use `uv sync --locked`, `uv run pytest`, `uv run ruff check .` and `uv build`.
Keep CLI discovery in catalog.py, execution in runner.py, the reusable screen in
panel.py and the standalone host in app.py. Public exports belong in __init__.py.

Discover commands using local gh help only. Never execute discovered aliases or
extensions during catalog loading. Execute argv without a shell. Preserve command
previews, explicit execution, cancellation/timeouts and repository context.
Do not persist command output or credentials. Use fixture commands in tests;
live smoke tests may use read-only GitHub operations only.

This repository is public. Commit only project code and documentation; exclude
local state, credentials, private source-project data and generated build files.
Retain LICENSE and NOTICE.md. Keep prompts.md and memory.md current, increment
their versions/deltas and the release version when appropriate, and commit changes.

## Contributor orientation

Read [CLAUDE.md](CLAUDE.md) for shared commands and workflow logging, then
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Keep generated operations metadata
and documentation indexes current with the scripts listed there.

## Repo-local agents

There are no agent definitions under `.claude/agents/` or `.github/agents/`.
There is no repo-local model, tool, credential, or authentication requirement for
agent execution. User-level agents and MCP tools are outside this repository.
If agents are added, inventory their names, scope, models, invocation conditions,
and required auth here, with links to their definitions.
