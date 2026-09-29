# Error diagnosis

## Where to look

Read the TUI status and Output tab, or stderr for CLI startup errors. Terminal-mode
errors stay in the terminal. There is no central error log, scheduled monitor,
or automatic remediation agent. The application must not persist command output
or credentials. See [logging](logging.md).

## Failure map

| Observed failure | Likely boundary | Action / retry policy |
| --- | --- | --- |
| `GitHub CLI (gh) is not installed or is not on PATH` | `catalog.executable` | Install/fix PATH, then retry explicitly |
| Invalid directory or repository message | CLI / `runner.prepare` | Correct input; do not retry unchanged |
| Local help failure or timeout | `catalog.help_text` | Inspect `gh help reference` and `gh --help`; reload only after resolving cause |
| Nonzero command exit | Captured/terminal child | Inspect sanitized error, permissions, and command semantics before retrying |
| Cancelled / timed out | Captured runner | Check whether side effects already completed before retrying |
| Capture truncated | Runner output bound | Narrow the request; do not increase retention without evaluating privacy/memory |
| Authentication/authorization failure from gh | GitHub CLI or GitHub | Correct account/scopes outside the app; never auto-retry credential failures |

No automatic retry occurs at the Explorer layer. A timeout or cancellation does
not prove a GitHub mutation failed; verify state with an authorized read-only
command before deciding to reissue it. Commands and extensions may apply their
own retries independently.

## Escalation

Use [the troubleshooting runbook](runbooks/troubleshooting.md) and file a sanitized
reproduction using the issue template. For suspected credential exposure or a
vulnerability, follow [security reporting](../.github/SECURITY.md). No on-call or
response-time SLA is established.
