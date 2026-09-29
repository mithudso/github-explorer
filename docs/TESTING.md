# Testing

## Strategy and suites

The suite combines pure parsing tests, fixture subprocess integration tests, and
headless Textual interactions. It does not mutate live GitHub data.

| Suite | Command | Main coverage |
| --- | --- | --- |
| Catalog | `uv run pytest tests/test_catalog.py` | Reference/flag parsing, aliases and extensions |
| Runner | `uv run pytest tests/test_runner.py` | Exact argv/context, capture, exit status, cancellation, timeout, limits, terminal delegation |
| CLI | `uv run pytest tests/test_cli.py` | Help/version, invalid context, missing gh, JSON inventory, standalone host |
| Panel | `uv run pytest tests/test_panel.py` | Confirmation/cancel, argument editing, captured/terminal execution, stop, embed dismissal |
| Shortcuts/navigation | `uv run pytest tests/test_shortcuts.py tests/test_navigation.py` | All twelve buttons/hotkeys, no execution before confirmation, Git scope, responsive bar, tree arrows, directional focus, dropdowns and editing |
| Repository | `uv run pytest tests/test_repository.py tests/test_repository_panel.py` | Read-only metadata/trees/blobs, errors, host context, file browser, settings selection/cancel/confirm and stale reads |
| Maintenance | `uv run pytest tests/test_maintenance.py tests/test_doc_indexes.py` | Rotation safety, metadata drift, index generation, private-file exclusions |
| All tests | `uv run pytest` | Every collected test under `tests/`, including maintenance tooling tests |

## Writing tests

Use `test_*.py` and `test_*` names. Use `tmp_path` for isolated files and
`monkeypatch` for the executable, help data, and execution boundaries. Fixture
subprocesses use `sys.executable` rather than GitHub authentication. UI tests use
`App.run_test()` and await workers before asserting observable state. Assert the
result and relevant negative effects, such as no execution before confirmation.
Do not merely assert that a function ran.

## Targets and CI gates

The target is meaningful coverage of important and changed/risky behavior. No
numeric line-coverage threshold, coverage-report command, or blanket 100% mandate
is configured. Pytest assertions are the behavioral gate. CI also runs Ruff,
package builds, operations-document drift checks, and index path validation on
macOS/Linux with Python 3.11/3.14. See [.github/workflows/test.yml](../.github/workflows/test.yml).

Before submitting:

```sh
uv sync --locked
uv run pytest
uv run ruff check .
uv build
uv run python scripts/generate_ops_registry_doc.py --check
uv run python scripts/check_doc_indexes.py
```

## Limitations and smoke checks

Fixtures do not prove every installed `gh` version, alias, extension, terminal,
auth flow, or GitHub Enterprise deployment works. Windows is not in the supported
CI matrix. Terminal-mode interaction needs manual verification in a real terminal.
A safe local smoke check is `uv run github-explorer --list-commands`; this reads
local CLI help. Optional live smoke commands must be read-only, explicitly selected,
and must not persist sensitive output. See [logging](logging.md) for privacy rules.

UI tests use `ui_repository` from `tests/conftest.py` to replace automatic GitHub reads.
Tests never require network credentials or mutate real repository settings.
