# Installation

## Prerequisites

Use macOS or Linux, Python 3.11+, `uv`, a terminal, GitHub CLI (`gh`), and Git (`git`) on PATH.
Install Vim on PATH for editing selected local files.
No hardware minimum is measured; a 120-column by 40-row terminal is recommended
for the layout. No server, database, Node.js runtime, or MCP server is required.

## Install

```sh
uv tool install git+https://github.com/mithudso/github-explorer.git
github-explorer --version
github-explorer --list-commands
github-explorer --cwd ~/dev/my-project
```

`ghx` is an equivalent entry point. `--list-commands` reads local help and prints
JSON. Authenticate using `gh auth login` before running operations that need an
account. The app uses that existing authentication.

For development from a clone:

```sh
git clone https://github.com/mithudso/github-explorer.git
cd github-explorer
uv sync --locked
uv run github-explorer --cwd .
```

An optional `--repo owner/name` or `--repo host/owner/name` overrides repository
context for commands that support it. The TUI also exposes both context fields.

## Verification

Run `github-explorer --help` and `github-explorer --version` after tool installation.
The catalog smoke check above requires `gh`; help and version do not. In a clone,
use `uv run pytest`, `uv run ruff check .`, and `uv build` for project validation.
Confirm the preview before any actual GitHub action.

## Upgrade and uninstall

Upgrade an installed tool with `uv tool upgrade github-explorer`. For a checkout,
review/preserve local changes, update from the remote, then run `uv sync --locked`
and the checks in [development](DEVELOPMENT.md). For a reproducible installation,
use a reviewed Git tag or commit in the Git URL.

Remove the tool with `uv tool uninstall github-explorer`. Removing a development
checkout also removes its local environment if `.venv` resides inside it; preserve
any uncommitted work first. GitHub CLI, its credentials, and its extensions are
separate and are not removed by uninstalling Explorer.
