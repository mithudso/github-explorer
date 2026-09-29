# CLI and operations

## User entry points

`github-explorer` and `ghx` both call `github_explorer.__main__:main`.
`python -m github_explorer` is equivalent in the installed environment.

| Option | Behavior |
| --- | --- |
| `--help` | Print usage without inspecting gh |
| `--version` | Print package version without inspecting gh |
| `--cwd PATH` | Use an existing directory; defaults to launch directory |
| `--repo [HOST/]OWNER/REPO` | Set explicit repository context for supporting commands |
| `--list-commands` | Read local help and print command/description/external JSON |

With no inventory/help option, the command opens the TUI and reads the GitHub
file list above the CLI catalog. A matching checkout uses local files and embedded
Vim; remote-only contexts use read-only default-branch previews.
Repo settings opens the CLI-derived form; checked changes require confirmation.
Choose a command, edit
arguments, then use Run or Terminal and approve the preview. Run captures bounded
output with timeout/Stop. Terminal supports normal stdin/editors and suspends the
TUI. No generic `run <operation-id>`, history, or reset CLI is implemented.

## TUI shortcuts

The bottom action bar pairs twelve buttons with F1–F12: Status, Pull, Push, Fetch,
Diff, Stage, Commit, PR, CO, Merge, PR List and Checks. Each requires confirmation.
The [command and navigation table](../README.md#common-commands-and-keyboard-navigation)
documents exact argv, terminal modes and arrow behavior. The Git menu adds curated
local commands; `--list-commands` still exports only the installed gh catalog.

## Maintenance registry

`src/github_explorer/operations.py` declares the existing subprocess and clipboard boundaries.
`scripts/generate_ops_registry_doc.py` writes
[operations-registry.json](operations-registry.json) and
[tool-inventory.json](tool-inventory.json). Regenerate and validate from the root:

```sh
uv run python scripts/generate_ops_registry_doc.py
uv run python scripts/generate_ops_registry_doc.py --check
```

This registry documents existing behavior; it grants no additional execution
capability. Persistent history, service dashboard cards, automatic remediation,
and datastore verification do not apply to the app. GitHub mutations cannot be
verified generically without command-specific permissions and semantics. Users
must inspect the requested operation's own result. See [external calls](external-calls.md)
for the full applicability assessment.
