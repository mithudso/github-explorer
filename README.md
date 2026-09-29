# GitHub Explorer

A standalone terminal workbench for GitHub repositories and the installed GitHub
CLI. Browse repository files, edit settings, read command help, and run Git and
GitHub operations without leaving your TUI.

Built from the reusable GitHub panel with a public, self-contained Python package.

## Install and run

Requires Python 3.11+, [GitHub CLI](https://cli.github.com/) and Git on PATH, and a terminal.
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

- Browse and search default-branch files from GitHub above the CLI command tree.
  Select a file for a read-only text preview; local uncommitted files are not shown.
- Open **Repo settings** to see every option exposed by local `gh repo edit --help`,
  view current values where available, and review selected changes before applying.
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
The command catalog comes from local `gh help reference` and `gh --help`. Opening
the app also makes read-only GitHub requests for the repository and its default-branch
file tree. Command availability follows your installed GitHub CLI version. Raw entry supports commands and extension
subcommands that the generated reference does not list.

For shell-friendly inventory without opening the TUI:

```sh
github-explorer --list-commands
python -m github_explorer --help
```

## Common commands and keyboard navigation

The bottom buttons and F1–F12 open the same command preview. Nothing runs until
**Run** is confirmed. Cancel to edit the populated command before using **Run** or
**Terminal**. On keyboards that reserve function keys for media controls, use Fn
with the function key or configure the terminal to send F1–F12.

| Key / button | Command | Mode |
| --- | --- | --- |
| F1 Status | `git status --short --branch` | Captured |
| F2 Pull | `git pull --ff-only` | Captured |
| F3 Push | `git push` | Captured |
| F4 Fetch | `git fetch` | Captured |
| F5 Diff | `git diff` | Captured |
| F6 Stage | `git add --patch` | Terminal |
| F7 Commit | `git commit` | Terminal |
| F8 PR | `gh pr create` | Terminal |
| F9 CO | `gh pr checkout` | Terminal |
| F10 Merge | `gh pr merge` | Terminal |
| F11 PR List | `gh pr list` | Captured |
| F12 Checks | `gh pr checks` | Captured |

Pull and push belong to Git. Find them under **Git · local checkout** in the
command tree, alongside switch, merge, log and the other Git shortcuts. Direct Git
commands use the working directory and its configured remotes; the GitHub repository
field does not redirect them. Pull refuses divergent history with `--ff-only`.
Push uses the checkout's configured push settings without adding a force flag.

Stage selects tracked-file changes interactively; use `git add -- PATH` to add new
files. Commit includes already-staged changes. Diff shows unstaged changes; add
`--staged` for the index. CO checks out a pull request; use `git switch BRANCH` for a
local branch. Merge merges the current branch's PR; use `git merge BRANCH` for a
local merge. Terminal handles prompts and editors for these interactive actions.
If a captured command needs authentication input, cancel its preview and use Terminal.
`--list-commands` continues to export only the installed `gh` catalog.

- **Down** expands a collapsed file/command branch. On an expanded branch or leaf,
  it moves to the next visible item. At the end of a tree, it moves to the control below.
- **Up** moves to the previous item or the control above the tree.
- **Right** expands a branch, enters its first child, or moves to the control on the right.
- **Left** collapses a branch, returns to its parent, or moves to the control on the left.
- On buttons and other controls, arrows move focus in that direction. Dropdowns
  open with Up/Down; their arrows and Enter retain normal option selection.
- Text fields keep Left/Right for editing; Up/Down moves between controls. Multiline
  editors retain their own cursor navigation. Previews and output scroll within
  their content; at a boundary, arrows move to nearby controls. **Tab/Shift+Tab**
  always move between controls. Arrows do not select a file or run a command;
  use **Enter** to activate the focused item.

Navigation also works in repository settings and command confirmation dialogs.

## Files and repository settings

The left pane starts with repository files; the CLI tree remains underneath. Expand
folders or use **Find a repository file** to reveal matching paths. The default
**Repository files** tab previews the selected blob from GitHub in memory. Binary,
non-UTF-8 and files larger than 500 KB have an explanatory placeholder. Submodule
entries show their commit. Empty repositories show zero files; failed reads show
an error without disabling the CLI tree.

Press Enter after changing the working directory or repository field, or click
**Refresh files**. This reads the GitHub default branch, even when your local
checkout is on a different branch. Unpushed changes appear after pushing and refreshing.

**Repo settings** loads the installed CLI's editable flags and current GitHub values.
Check **Change** for each option to submit, then choose **Review changes**. Only
checked options enter the command; empty description/homepage fields clear those
values, and boolean options support both true and false. Unknown or permission-hidden
values are labeled rather than assumed false. Topic actions accept comma-separated
names. Unsupported values, organization policies and permissions are enforced by GitHub.

Review the exact repository, directory and argv, then **Run** or **Cancel**. Cancelling
keeps the form and its draft values. Visibility changes also require selecting and
enabling `--accept-visibility-change-consequences`. Changing the squash message
format also requires selecting and enabling `--enable-squash-merge`. The dialog pins its target when
loaded. After execution the file browser refreshes; reopen settings to read current
values, especially if a command failed or was cancelled after partial changes.

## Execution behavior

Captured mode disables prompts, combines stdout/stderr, limits retained output to
two million characters and supports cancellation/timeouts. Use Terminal when a
command requires prompts or stdin. Stop cannot undo completed local or remote actions.

Commands run as argument arrays, without shell expansion, redirection or pipelines.
Use native CLI options such as `--body-file`, `--input`, `--json`, `--jq` or
`--template`. Installed aliases and extensions retain their own behavior.

The directory controls local checkout actions. The optional repository field sets
`GH_REPO` for GitHub CLI commands that support it; direct Git commands ignore it.
A GitHub CLI command's explicit `--repo` takes precedence.
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
