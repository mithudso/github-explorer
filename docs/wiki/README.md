# Project wiki

This is the versioned wiki for GitHub Explorer. Keep it current in the same pull
request as a behavior, command, or maintenance change. The linked guides own the
details; update those guides instead of duplicating them here.

## Start here

- [Install and run](../INSTALLATION.md): Homebrew, npm, Python and source checkouts.
- [User guide](../../README.md): navigation, file editing, command previews and settings.
- [Contributor onboarding](../onboarding.md) and [development](../DEVELOPMENT.md).
- [Architecture](../ARCHITECTURE.md), [components](../COMPONENTS.md), and
  [source map](../codebase-overview.md).

## Verified contributor commands

Run these from the repository root. Python checks use the committed uv lockfile.
The npm launcher tests use Node.js 18 or newer; CI uses [.node-version](../../.node-version).

```sh
uv sync --locked
uv run github-explorer --cwd .
uv run pytest
uv run ruff check .
uv build
npm --prefix npm test
uv run python scripts/generate_ops_registry_doc.py --check
uv run python scripts/check_doc_indexes.py
```

[Testing](../TESTING.md) explains fixture isolation, real Vim checks and the
macOS/Linux Python 3.11/3.14 CI matrix. Live smoke checks use read-only operations.

## Scripts and operating references

| Task | Script / guide |
| --- | --- |
| Refresh operation metadata | `uv run python scripts/generate_ops_registry_doc.py`; [external calls](../external-calls.md) |
| Refresh static source indexes | `uv run python scripts/generate_repo_indexes.py --refresh`; [metadata runbook](../runbooks/metadata-maintenance.md) |
| Check index drift | `uv run python scripts/check_doc_indexes.py` |
| Plan workflow-log rotation | `uv run python scripts/rotate_workflow_logs.py`; use `--apply` only with writers idle |
| Stage release distributions | `uv run python scripts/build_distributions.py`; [release guide](../RELEASING.md) |
| Diagnose failures | [Troubleshooting](../runbooks/troubleshooting.md), [known limits](../known-issues.md), [error guide](../error-monitoring-guide.md) |

## Design and maintenance direction

Keep local-help discovery in `catalog.py`, explicit execution in `runner.py`,
the reusable screen in `panel.py`, and standalone hosting in `app.py`. Preserve
confirmation, cancellation, output bounds, repository context and Vim's unsaved
buffers. Commands and local editing cannot run together. Remote previews remain
read-only.

The app keeps command output in memory. It owns no server, datastore, durable
error sink or MCP runtime. Static documentation indexes require no embedding
service or watcher. See [security](../SECURITY.md), [logging](../logging.md),
[integration assumptions](../integrations-and-assumptions.md), and
[MCP applicability](../MCP.md).

Release publication is manual. Main's package version may be newer than published
artifacts; the checked-in Homebrew formula describes the last published archive.
See the [changelog](../../CHANGELOG.md) and [release procedure](../RELEASING.md)
before publishing. The [bootstrap audit](../repo-bootstrap-audit-2026-11-12.md)
records the latest standards review and its limits.
