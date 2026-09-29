# External calls

Runtime boundaries are declared in [operations.py](../src/github_explorer/operations.py).
Regenerate the JSON inventory with `python3 scripts/generate_ops_registry_doc.py`.
The metadata never executes commands. `gh` owns GitHub transport, authentication,
API retries, and any local/remote side effects. The explorer does not add retries.

| Source and symbol | Target / trigger | Observation | Tests | Retry policy |
| --- | --- | --- | --- | --- |
| `catalog.py:help_text` | Local help subprocesses: `gh help reference`, `gh --help`, `gh repo edit --help`; startup, Reload catalog, settings dialog or `--list-commands` | TUI status or CLI stderr; 30-second help timeout | `test_catalog.py`, `test_cli.py` | Manual reload after repairing cause |
| `runner.py:read_json` | Read-only `gh repo view` identity and explicit `gh api --method GET` metadata, trees and blobs; startup, Refresh files, selection, settings dialog | In-memory UI status/content; 30-second timeout per request; truncation rejected | `test_repository.py`, `test_repository_panel.py` | User-triggered refresh; no automatic retry |
| `runner.py:CommandRunner.run` | Confirmed command/settings argv or fixed repository-read argv via `Popen` | Ephemeral output and Result: exit, cancellation, timeout, truncation | `test_runner.py`, `test_panel.py` | Never replay automatically; verify remote side effects first |
| `runner.py:run_interactive` | Confirmed argv via `subprocess.call`; Terminal | Attached terminal output and exit status; Ctrl-C maps to 130 | `test_runner.py`, `test_panel.py` | Manual only; no captured-mode timeout |
| `panel.py:GitHubPanel.pressed` | `App.copy_to_clipboard`; Copy output button | In-memory status; clipboard receipt cannot be verified | `test_panel.py` | User-directed; terminal support varies |

Source files live under `src/github_explorer/`; tests live under `tests/`.
The registry generator checks source paths. Test and CI subprocesses use fixture
programs, Python tooling and Git read commands; they do not execute discovered aliases
or mutate GitHub. Documentation generators use local reads and explicit generated-file
writes; the rotation script archives local documentation only with `--apply`.

## Applicability of the five-standard service contract

| Standard | This desktop application |
| --- | --- |
| Named trigger | Each runtime boundary has a named CLI or TUI trigger in the registry. There is no generic operation dispatcher. |
| Central error JSONL | Intentionally absent: persisted command arguments, errors and output would conflict with the transient-data rule. UI status and terminal/CLI output carry errors. |
| Automatic remediation | Registry entries give human repair guidance. They are outcome categories, not emitted runtime error codes. Arbitrary `gh` writes cannot be safely replayed automatically. |
| Dashboard cards | No server dashboard exists. The TUI exposes preview, output, status, Stop, Clear output and explicit rerun. |
| Datastore verification | `verifyDatastore: false`: the explorer owns no datastore. This does not verify a `gh` action succeeded remotely; inspect GitHub before retrying a cancelled or failed command. |

This is an adapted local-app baseline, not a claim of compliance with the full service
contract. See [logging](logging.md), [security](SECURITY.md) and the
[error guide](error-monitoring-guide.md).
