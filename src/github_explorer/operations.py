"""Declarative inventory for maintainers; never executes or retries commands."""

OPERATIONS = (
    {
        "id": "catalog-help",
        "kind": "check",
        "transport": "subprocess",
        "target": "gh help reference; gh --help; gh repo edit --help (separate argv calls)",
        "description": "Discover local CLI help without running discovered commands.",
        "sourceFile": "src/github_explorer/catalog.py",
        "sourceSymbol": "help_text",
        "readOnly": True,
        "verifyDatastore": False,
        "trigger": "github-explorer --list-commands, Reload catalog or Repo settings",
        "retryPolicy": "No automatic retries; correct the error and reload manually.",
        "observability": "In-memory TUI status or CLI stderr; no persistent log.",
        "tests": ["tests/test_catalog.py", "tests/test_cli.py"],
        "remediation": {
            "missing-executable": "Install GitHub CLI and check PATH.",
            "spawn-error": "Check directory existence and permissions.",
            "help-failed": "Inspect the displayed CLI error; repair local gh configuration.",
            "timeout": "Check the local gh installation, then retry explicitly.",
        },
    },
    {
        "id": "repository-read",
        "kind": "check",
        "transport": "subprocess",
        "target": "gh repo view identity; gh api --method GET repository metadata, trees and blobs",
        "description": "Read GitHub default-branch files, previews and current repository settings.",
        "sourceFile": "src/github_explorer/runner.py",
        "sourceSymbol": "read_json",
        "readOnly": True,
        "verifyDatastore": False,
        "trigger": "Panel entry, Refresh files, file selection and Repo settings",
        "retryPolicy": "No automatic retry; refresh explicitly after resolving the cause.",
        "observability": "In-memory file list, preview, settings form or error status; no persistence.",
        "tests": ["tests/test_repository.py", "tests/test_repository_panel.py"],
        "remediation": {
            "read-failed": "Check repository context, gh authentication, permissions and API limits.",
            "cancelled": "Select a file or refresh the repository to start another read.",
            "timeout": "Check connectivity and explicitly refresh.",
            "truncated": "Use gh directly for a response exceeding the app's bounded capture.",
            "invalid-json": "Inspect the CLI installation and GitHub API response.",
        },
    },
    {
        "id": "captured-command",
        "kind": "command",
        "transport": "subprocess",
        "target": "User-confirmed gh or git argv and their child processes",
        "description": "Run a confirmed command with bounded output and cancellation.",
        "sourceFile": "src/github_explorer/runner.py",
        "sourceSymbol": "CommandRunner.run",
        "readOnly": False,
        "warning": "Commands, aliases, extensions and Git hooks can change local and remote data.",
        "verifyDatastore": False,
        "trigger": "Run, captured shortcut or Repo settings / Review changes, then confirm",
        "retryPolicy": "Never automatically replay commands; side effects may have completed.",
        "observability": "In-memory output, exit status, cancellation and timeout indicators.",
        "tests": ["tests/test_runner.py", "tests/test_panel.py", "tests/test_shortcuts.py"],
        "remediation": {
            "invalid-input": "Correct argv, working directory, repository or timeout.",
            "spawn-error": "Check gh/git installation and working directory permissions.",
            "nonzero-exit": "Read the captured error and verify side effects before retrying.",
            "cancelled": "Verify remote state; Stop cannot undo completed actions.",
            "timeout": "Verify remote state before explicitly retrying.",
            "truncated": "Use narrower gh output options; retained output is bounded.",
        },
    },
    {
        "id": "terminal-command",
        "kind": "command",
        "transport": "subprocess",
        "target": "User-confirmed gh or git argv in the user's terminal",
        "description": "Suspend the host TUI for an interactive command.",
        "sourceFile": "src/github_explorer/runner.py",
        "sourceSymbol": "run_interactive",
        "readOnly": False,
        "warning": "Commands can prompt, write files, change GitHub data or run extensions.",
        "verifyDatastore": False,
        "trigger": "Terminal or interactive shortcut, then confirm the command preview",
        "retryPolicy": "No automatic retries; inspect side effects before retrying manually.",
        "observability": "Terminal output and in-memory exit status; no capture or log file.",
        "tests": ["tests/test_runner.py", "tests/test_panel.py", "tests/test_shortcuts.py"],
        "remediation": {
            "spawn-error": "Check executable and working directory access.",
            "nonzero-exit": "Inspect terminal diagnostics; verify side effects before retrying.",
            "interrupted": "Ctrl-C returns 130; verify remote state before retrying.",
            "suspend-unsupported": "Use a host supporting App.suspend() for terminal mode.",
        },
    },
    {
        "id": "copy-output",
        "kind": "command",
        "transport": "terminal-clipboard",
        "target": "Textual App.copy_to_clipboard and the user's terminal clipboard",
        "description": "Copy the last captured output only after an explicit button press.",
        "sourceFile": "src/github_explorer/panel.py",
        "sourceSymbol": "GitHubPanel.pressed",
        "readOnly": False,
        "warning": "The clipboard may retain sensitive captured output outside the app.",
        "verifyDatastore": False,
        "trigger": "Copy output",
        "retryPolicy": "No automatic retries; terminal clipboard support varies.",
        "observability": "In-memory copy status; clipboard receipt is not verified.",
        "tests": ["tests/test_panel.py"],
        "remediation": {
            "clipboard-unavailable": "Check terminal clipboard support and select text manually.",
        },
    },
)


def list_operations() -> tuple[dict, ...]:
    """Return independent metadata copies, with no discovery or execution side effects."""
    from copy import deepcopy

    return deepcopy(OPERATIONS)


def get_operation(operation_id: str) -> dict:
    """Return a metadata entry or raise KeyError for an unknown operation."""
    for entry in list_operations():
        if entry["id"] == operation_id:
            return entry
    raise KeyError(operation_id)
