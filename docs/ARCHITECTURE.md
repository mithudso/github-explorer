# Architecture

## Context and containers

GitHub Explorer is a local terminal application for a person using an installed
GitHub CLI. It supplies discovery, argument editing, confirmation, and output
handling. GitHub CLI owns authentication, API access, Git operations, aliases, and
extensions. The application has no listening port or persistent datastore.

```text
Person / terminal
        |
Python process: GitHubExplorer (standalone) or another Textual 8 host
        |
GitHubPanel --- catalog.load_catalog --- gh help reference / gh --help
        |
CommandConfirm --- runner.prepare --- CommandRunner / run_interactive
                                        |
                                  installed gh process
                                        |
                       checkout / GitHub / user-installed tools
```

The subprocess boundary is also a trust boundary: user-installed `gh`, aliases,
and extensions can perform actions beyond a repository. See [security](SECURITY.md).

## Components

`__main__.py` validates startup options. `app.py` mounts the reusable screen.
`panel.py` owns widgets and background workers. `catalog.py` parses local help into
command/flag records, including settings from `gh repo edit --help`. `runner.py`
owns invocation context, subprocess lifecycle, repository metadata/tree reads and
bounded blob previews.
`operations.py` describes these and clipboard boundaries for generated maintenance metadata;
it is not a second command executor. [Components](COMPONENTS.md) lists APIs.

## Runtime views

1. Startup validates the working directory and optional repository override.
2. The catalog worker runs two local help commands, parses them, and populates the tree.
3. An independent worker resolves the repository and host, then reads the default-branch
   Git tree one directory at a time. File selection reads a blob by immutable SHA.
   Stale or cancelled workers cannot replace a newer repository or preview.
4. CLI selection loads cached help; argument widgets quote each appended argument.
5. Run or Terminal prepares argv and shows the exact directory/repository/command.
6. Confirmation starts execution. Captured mode streams bounded output; terminal
   mode suspends Textual and attaches the child to the terminal.
7. Completion updates the screen. Stop requests cancellation in captured mode.
   Closing a busy screen is blocked; unmount requests cancellation.

## Deployment and quality attributes

One Python 3.11+ environment runs on macOS or Linux with `gh` on PATH. Textual 8
and Rich are installed from the Python dependency metadata. Terminal layout is
most comfortable around 120×40 or larger. There is no throughput/latency SLA.
Help subprocesses have a 30-second timeout each. Captured commands default to
300 seconds; the UI accepts values greater than zero and at most 86400 seconds.
Terminal mode uses the terminal's normal lifecycle and has no application timeout.

## Architectural decisions

- **Local discovery:** derive commands from installed help so catalog availability
  follows the user's CLI. Do not run aliases/extensions to expand the catalog.
- **Reusable screen:** keep hosting separate so other Textual apps can embed the UI.
- **Explicit argv execution:** avoid shell expansion and require confirmation to
  make directory and repository context visible before execution.
- **Volatile output:** keep command output in memory. This prevents a new on-disk
  copy of private output or credentials. GitHub CLI and executed tools retain
  their own behavior and may write files when the user requests those operations.
- **Language-native maintenance:** use Python scripts for generated metadata;
  service-specific dashboards, MCP servers, and persistent error sinks do not
  apply to this local app.

## Repository settings

`RepoSettings` loads all local `gh repo edit` flags and a REST metadata snapshot.
Known REST properties prefill fields; missing values remain unknown. Only checked
fields are converted to argv. The dialog resolves and freezes the GitHub host/name,
then confirms `gh repo edit https://HOST/OWNER/REPO ...` before handing execution to
the existing runner. Closing or cancelling a draft never writes to GitHub. Each
read has a 30-second timeout; closing the panel cancels outstanding read processes.

The file list uses nonrecursive trees to avoid GitHub's recursive-tree size limit;
if even a directory is truncated, it reports an error rather than a partial list.
Source: [GitHub Git trees API](https://docs.github.com/en/rest/git/trees#get-a-tree).

Squash-message current values map the REST title/message pair back to CLI modes,
following the [GitHub CLI editor implementation](https://github.com/cli/cli/blob/trunk/pkg/cmd/repo/edit/edit.go).
