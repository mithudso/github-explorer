# Requirements

## Functional requirements

1. Discover command paths and flags from local installed `gh` help.
2. Include aliases/extensions from root help without executing them during discovery.
3. Search commands and display help in a reusable Textual screen.
4. Edit raw commands and append separately quoted flags/arguments.
5. Show the exact argv, working directory, and repository override before execution.
6. Execute user commands and settings changes only after confirmation, without an application shell.
7. Support captured output with cancellation and timeout, and explicit terminal mode.
8. Preserve repository context and normal account/organization command scope.
9. Expose `github-explorer`, `ghx`, module invocation, and local catalog JSON export.
10. Keep captured output volatile; copy it only on an explicit user action.
11. Load GitHub default-branch files by default above the existing CLI tree; support search and previews.
12. Discover all repo edit options from installed help, display available current values, and confirm selected changes.

13. Provide common Git/GitHub actions as matching bottom buttons and F1–F12 bindings.
14. Expand/navigate trees and move focus using arrows while preserving text editing.
15. Keep direct Git working-directory scope distinct from the GitHub repository override.

## Non-functional requirements

Support Python 3.11+ on macOS/Linux and Textual 8 embedding. Bound retained captured
text to two million characters and the visible RichLog to 5000 lines. Keep CLI
help calls bounded to 30 seconds each. No measured hardware minimum, concurrency
SLA, startup-time target, or Windows compatibility guarantee is established.
Preserve the privacy and process-boundary requirements in [security](SECURITY.md).

## Dependencies

`pyproject.toml` defines allowed ranges; `uv.lock` is the authoritative resolved
set, including transitive dependencies. `uv sync --locked` installs that set.

| Dependency | Declared constraint | Purpose |
| --- | --- | --- |
| Python | `>=3.11` | Runtime |
| Textual | `>=8,<9` | Terminal UI and workers |
| Rich | `>=13` | Literal text/rendering |
| setuptools | `>=77` (build) | Wheel/source package backend |
| pytest | `>=8` (dev) | Test runner |
| pytest-asyncio | `>=0.24` (dev) | Async UI tests |
| Ruff | `>=0.11` (dev) | Lint and import checks |
| Git | Installed on PATH; no pinned version | Local checkout commands and shortcuts |
| GitHub CLI | Installed on PATH; no pinned version | Command discovery and execution |
| uv | Developer/install tool; no pinned version | Environment, lock, tests, build |

CI runs Python 3.11 and 3.14 on both supported operating systems. GitHub CLI version
and configuration determine command availability; fixture tests intentionally do
not constrain a live GitHub account or CLI installation.
