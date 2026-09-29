# Changelog

## 0.4.1 — 2026-09-29

- Package the complete TUI for Homebrew and npm with both command aliases.
- Pin distribution dependencies and validate packaged installation paths.
- Add release artifacts, checksums and documented publication commands.

## 0.4.0 — 2026-09-29

- Edit matching local checkout files in actual Vim embedded in the right pane.
- Save with :w, Ctrl+S or Save; preserve Vim's unsaved-file switch and close prompts.
- Keep remote-only repositories read-only and reject unsafe/non-text local paths.
- Show current branch, distinct changed files, open PRs and other branches in persistent status.
- Add a status details/refresh dialog and hide/show controls for bottom buttons and shortcuts.

## 0.3.0 — 2026-09-29

- Add twelve common Git/GitHub actions as bottom buttons and F1–F12 hotkeys.
- Add direct Git commands, a searchable local Git menu, and explicit checkout context.
- Keep preview/confirmation for shortcuts and terminal mode for interactive workflows.
- Use Down to expand collapsed branches and arrows to navigate trees and nearby controls.
- Preserve dropdown selection and text editing; support navigation in settings and confirmations.

## 0.2.0 — 2026-09-29

- Show searchable GitHub default-branch files above the CLI tree by default.
- Preview text files in memory, with explicit binary/size limits and cancellation.
- Add Repo settings with every installed gh repo edit flag and available current values.
- Confirm only selected settings changes against a pinned repository and host.
- Handle empty/inaccessible repositories and reject stale or truncated read results.
- Use Textual 8 unselected dropdown values in settings and the Add flag control.

## 0.1.1 — 2026-09-29

- Add contributor, architecture, security, operations and troubleshooting docs.
- Add deterministic static documentation and operation inventories with CI drift checks.
- Exclude symlinked source directories from generated public documentation.
- Add safe workflow-log rotation and regression coverage for maintenance tools.
- Ignore stale cancelled catalog loads and report help timeouts without a traceback.
- Preserve incomplete UTF-8 output at EOF and reject nonfinite execution timeouts.

## 0.1.0 — 2026-09-29

- Extract the reusable GitHub panel into a standalone public project.
- Add github-explorer and ghx launchers, repository selection and catalog export.
- Browse the installed gh command suite, read help, build flags and arguments,
  preview commands, capture output, cancel jobs or run interactive terminal flows.
- Retain the GitHubPanel screen for embedding in other Textual applications.
