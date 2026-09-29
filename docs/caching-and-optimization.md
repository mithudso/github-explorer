# Caching and performance

## In-memory state

`GitHubPanel.commands` holds the parsed catalog for the mounted screen. Selecting
a command uses its stored help and flags. Reload catalog reruns both local help
calls and replaces the list; restarting also discards it. Search filters existing
records and rebuilds the tree; it does not call `gh` on each keystroke.

`last_result` retains the most recent captured result until the next run, Clear
output, or screen disposal. Captured text is bounded to two million characters;
visible log lines are bounded to 5000. There is no on-disk, database, shared,
HTTP/CDN, or cross-session cache.

## Work scheduling and limits

Catalog and execution work run on Textual workers so blocking subprocess activity
does not run directly in UI callbacks. Captured execution uses selector-based
reads and checks cancellation/deadline between polls. It drains output beyond the
capture limit without retaining the additional text. Only one user command runs
through a panel at a time. Help calls are sequential and may each take up to
30 seconds; command counts depend on the installed CLI.

Potential bottlenecks are help generation, rebuilding a large search tree, and
frequent UI output updates. Profile before adding caching, concurrency, or batching;
never bypass explicit execution or retain private output to improve speed.

## Profiling

For an optional disposable local profile:

```sh
uv run python -m cProfile -s cumulative -m github_explorer --list-commands
```

This prints profiling data and the catalog to the terminal without writing a
profile artifact. Inspect time spent in help subprocess calls versus parsing.
Use fixture tests to measure runner/UI changes; avoid benchmarking destructive
GitHub operations. No performance SLA or benchmark gate is currently configured.

## Repository data

File lists, settings snapshots and the selected preview exist only in memory.
Refresh files cancels previous reads and reloads local checkout files or the
remote default-branch tree. Selecting another remote file cancels the previous
preview; local file switches reuse one Vim process and its unsaved-buffer prompt. Context/worker guards discard
late results. Each directory uses one GET request; there is no disk cache or retry
loop. Tree size and GitHub rate limits constrain very large repositories.

Local branch/change status polls every two seconds without overlapping workers.
GitHub PR/branch status polls every minute, paginates and keeps only projected
status fields in memory. Context changes cancel stale reads. Vim uses an embedded
PTY without persistent session files; explicit saves are source edits, not a cache.
