# Components

## Application modules

| Module | API / inputs → outputs | Dependencies and side effects |
| --- | --- | --- |
| `src/github_explorer/__init__.py` | Exports `GitHubExplorer`, `GitHubPanel`; `__version__` identifies the release | Imports host and screen; keep public exports here |
| `src/github_explorer/__main__.py` | `main(argv=None)` parses startup options; exits/returns a status | argparse, catalog, app; starts TUI or prints catalog JSON |
| `src/github_explorer/app.py` | `GitHubExplorer(cwd=".", repo="")` hosts one panel | Textual; exits when standalone panel dismisses |
| `src/github_explorer/panel.py` | `GitHubPanel(repo_path=".", repo="", standalone=False)`; `CommandConfirm(invocation, interactive, hint="")`; `ArrowNavigation`; `RepoSettings(context)` | Textual/Rich, catalog, runner; UI workers, confirmation, explicit clipboard copy |
| `src/github_explorer/catalog.py` | `Flag`, `Command`, `QuickAction`, `QUICK_ACTIONS`, `git_commands`, `flags_from_help`, `parse_catalog`, `executable`, `help_text`, `load_catalog`, `repository_settings`, `setting_value`, `settings_arguments` | Parses strings into immutable records; help calls local `gh` with 30-second timeout |
| `src/github_explorer/runner.py` | `Invocation`, `Result`, `prepare`, `git_executable`, `re_repo`, `CommandRunner`, `run_interactive`, `Repository`, `repository_info`, `repository_files`, `repository_file_text` | Validates argv/context; starts child processes; bounds captured output and manages stop/timeout |
| `src/github_explorer/operations.py` | `OPERATIONS`, `list_operations()`, `get_operation(id)` | Declares subprocess/clipboard metadata; returns independent copies; no execution path |

`parse_catalog(reference, root_help)` is pure. `load_catalog(cwd)` performs the two
help calls. `prepare(command, cwd, repo)` resolves the requested `gh` or `git` and the existing working
directory without executing it. `CommandRunner.run(invocation, on_output, timeout)`
returns a `Result`; `cancel()` requests termination. `run_interactive(invocation)`
returns the child status and must run while the host app is suspended.

## Embedding example

```python
from pathlib import Path
from github_explorer import GitHubPanel

# Inside a Textual 8 App method:
self.push_screen(GitHubPanel(Path.cwd(), repo="owner/repository"))
```

The host must support `App.suspend()` for Terminal mode. Escape dismisses an idle
embedded panel. The standalone host exits instead. Command output remains volatile.

## Maintenance tools and tests

| Path | Role |
| --- | --- |
| `scripts/generate_ops_registry_doc.py` | Generate operations/tool inventory artifacts and check drift |
| `scripts/generate_repo_indexes.py` | Generate repository navigation and LLM-readable file indexes |
| `scripts/check_doc_indexes.py` | Validate indexed paths |
| `scripts/rotate_workflow_logs.py` | Archive older oversized workflow-log sections, refusing active swap files |
| `tests/test_catalog.py` | Help parsing and discovery boundaries |
| `tests/test_runner.py` | Fixture subprocess behavior and execution safety |
| `tests/test_cli.py` | CLI options, catalog export, and standalone host |
| `tests/test_shortcuts.py` | Button/hotkey parity, modal/busy guards, Git menu and responsive bar |
| `tests/test_navigation.py` | Tree expansion, spatial focus, dropdowns, text editing and dialogs |
| `tests/test_panel.py` | Headless Textual interaction and embedding |
| `tests/conftest.py` | Network-free repository fixtures for UI tests |
| `tests/test_repository.py` | Host/context pinning, trees/blobs, read errors, setting discovery and argv |
| `tests/test_repository_panel.py` | Default file browsing, previews, settings confirmation and read races |
| `tests/test_maintenance.py` | Log rotation safety, registry copies, generated metadata |
| `tests/test_doc_indexes.py` | Index determinism, drift, inclusion boundaries, safe writes |

The dependency direction is CLI → host → panel → catalog/runner. Runner depends on
catalog only to resolve the executable. Maintenance scripts read source metadata;
they do not start GitHub commands. See [the generated file map](codebase-overview.md)
for the complete current file inventory.
