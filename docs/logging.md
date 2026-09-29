# Logging and output

## Current approach

The application exposes status messages and captured stdout/stderr in the TUI.
`CommandRunner` returns exit status, cancellation/timeout/truncation flags, and
bounded captured text. CLI startup failures are printed to stderr. These surfaces
are session-local; no application JSONL sink, rotating log file, remote collector,
or durable command history is configured.

Captured output is limited to two million characters; the visible RichLog is
limited to 5000 lines. Terminal execution delegates streams to the terminal and
does not capture its output. Explicit Copy output asks Textual to copy the last
captured result. Clear output clears the displayed/captured result when idle.

## Levels and diagnostics

There is no configured application logger or severity-level taxonomy. Success,
nonzero exit, cancellation, timeout, and truncation are represented by status and
`Result` fields. Do not describe these as a centralized structured logging system.
[The error guide](error-monitoring-guide.md) maps observable failures to next steps.

## Adding diagnostics

Preserve the no-persistence boundary. Prefer typed outcome fields and useful UI
messages with fixture assertions. Do not add disk logging of raw commands, argv,
environment values, credential-bearing errors, or command output. If a future
change requires durable telemetry, design an explicit opt-in and redaction policy
before implementation and update the security model.

Existing subprocess/UI tests assert outcomes and visible state. New failure paths
should assert the message or typed result and process cleanup, not merely that an
exception was caught. The generic bootstrap standard's persistent error log and
service dashboard are intentionally inapplicable to this application.
