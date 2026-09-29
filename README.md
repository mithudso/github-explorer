# GitHub Explorer

A standalone terminal workbench for the full installed GitHub CLI. Browse commands,
read their help, build arguments, and run GitHub operations without leaving your TUI.

Built from the reusable GitHub panel with a public, self-contained Python package.

## Install and run

Requires Python 3.11+, [GitHub CLI](https://cli.github.com/) on PATH, and a terminal.
macOS and Linux are supported. Authenticate using your existing `gh` configuration:

```sh
gh auth login
uv tool install git+https://github.com/mithudso/github-explorer.git
github-explorer --cwd ~/dev/my-project
# Short alias:
ghx --cwd ~/dev/my-project
```

From a checkout:

```sh
git clone https://github.com/mithudso/github-explorer.git
cd github-explorer
uv sync --locked
uv run github-explorer
# Or install globally from this checkout:
uv tool install .
```

The default working directory is where you launch the app. Use `--repo owner/name`
or `--repo hostname/owner/name` for an explicit GitHub repository. You can also
change both fields inside the TUI. Use a terminal around 120 columns by 40 rows
or larger for the most comfortable layout.

## What it does

- Discover and search the installed `gh` command catalog, including repository,
  PR, issue, Actions, release, project, discussion, API and administration commands.
- Select flags and add their values or positional arguments. Edit the command
  directly whenever you need an advanced combination.
- Preview the exact command, working directory and repository context before running.
- Capture output with **Run**, stop it with **Stop**, or configure a timeout.
- Use **Terminal** for authentication, editors, interactive PR flows, SSH/codespaces,
  extension installation and commands reading stdin. Return when the command exits.
- Use installed aliases and extension commands; reload the catalog after CLI changes.
- Copy captured output explicitly to your clipboard. Commands and output stay in
  memory and are never automatically saved to disk.

Select a command in the tree to open its help and populate the command editor.
Choose **Run** or **Terminal** when ready. **Escape** or **Quit** closes the app.
The catalog comes from local `gh help reference` and `gh --help`; opening the app
does not run GitHub API requests or repository actions. Command availability follows
your installed GitHub CLI version. Raw entry supports commands and extension
subcommands that the generated reference does not list.

For shell-friendly inventory without opening the TUI:

```sh
github-explorer --list-commands
python -m github_explorer --help
```

## Execution behavior

Captured mode disables prompts, combines stdout/stderr, limits retained output to
two million characters and supports cancellation/timeouts. Use Terminal when a
command requires prompts or stdin. Stop cannot undo completed GitHub actions.

Commands run as argument arrays, without shell expansion, redirection or pipelines.
Use native CLI options such as `--body-file`, `--input`, `--json`, `--jq` or
`--template`. Installed aliases and extensions retain their own behavior.

The directory controls local checkout actions. The optional repository field sets
`GH_REPO` for commands that support it. A command's explicit `--repo` takes precedence.
Account and organization commands retain their normal scope. Authentication uses
the installed GitHub CLI; the explorer does not store its own credentials.

## Reuse in another TUI

The `GitHubPanel` screen remains independent of the standalone host. Install this
package in another Textual 8 application's environment, then add a button or binding:

```python
from pathlib import Path
from github_explorer import GitHubPanel


def action_github(self):
    self.push_screen(GitHubPanel(Path.cwd(), repo="owner/repository"))
```

Escape returns to the host app. Terminal mode requires the host to support
`App.suspend()`; captured mode remains available without it. Widget IDs and styles
are scoped to the panel. No Skills Explorer installation is required.

## Development

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv build
```

Tests use fixture commands and mocked CLI catalogs. They do not mutate GitHub.
CI runs tests, lint and builds on macOS/Linux with Python 3.11 and 3.14.

MIT licensed. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md) for attribution.

## Documentation

- Getting started: [installation](docs/INSTALLATION.md), [onboarding](docs/onboarding.md),
  [requirements](docs/requirements.md).
- Design: [architecture](docs/ARCHITECTURE.md), [components](docs/COMPONENTS.md),
  [integrations and assumptions](docs/integrations-and-assumptions.md), [MCP applicability](docs/MCP.md).
- Engineering: [development](docs/DEVELOPMENT.md), [testing](docs/TESTING.md),
  [security model](docs/SECURITY.md), [logging](docs/logging.md),
  [caching and performance](docs/caching-and-optimization.md), [known limitations](docs/known-issues.md).
- Operations: [CLI and registry](docs/cli-and-operations.md), [external calls](docs/external-calls.md),
  [error diagnosis](docs/error-monitoring-guide.md), [troubleshooting](docs/runbooks/troubleshooting.md),
  [release and rollback](docs/runbooks/release-and-rollback.md),
  [metadata maintenance](docs/runbooks/metadata-maintenance.md).
- Navigation: [file map](docs/codebase-overview.md), [retrieval index](docs/high_signal_file_index.json),
  [operations metadata](docs/operations-registry.json), [tool inventory](docs/tool-inventory.json),
  [LLM entry point](docs/llms/llms.txt).
- Project workflow: [contributing](CONTRIBUTING.md), [code of conduct](CODE_OF_CONDUCT.md),
  [security reporting](.github/SECURITY.md), [agent instructions](AGENTS.md),
  [shared assistant conventions](CLAUDE.md), [Gemini conventions](GEMINI.md),
  [prompt history](prompts.md), [work log](memory.md), [changelog](CHANGELOG.md),
  [workflow archive](docs/archive/README.md).

The standalone host mounts the same reusable panel exported for embedding. The
panel delegates local help discovery to the catalog and confirmed subprocesses
to the runner; see [architecture](docs/ARCHITECTURE.md) for the data flow.
