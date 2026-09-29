# Known limitations and troubleshooting

This page records supported boundaries rather than an unverified bug backlog.
Update it when a reproducible issue is confirmed or fixed.

| Symptom / limitation | Cause and affected code | Workaround |
| --- | --- | --- |
| An extension subcommand is absent from the tree | `catalog.py` reads built-in reference and root help without executing extensions | Enter the command directly and inspect the confirmation |
| Run fails when a command needs input/editor/TTY | `runner.py` captured mode disables prompts and stdin | Use Terminal |
| Timeout/Stop unavailable while Terminal runs | `run_interactive` uses the normal terminal lifecycle; panel disables Stop | Use the command's normal exit or terminal interrupt; completed actions remain |
| Copy output omits older text after a very large response | `CommandRunner` retains at most two million characters; UI displays a bounded log | Narrow the command using native `gh` flags; do not add automatic output files |
| Catalog changes after upgrading `gh` are not immediately visible | `GitHubPanel` holds command records in memory | Reload catalog or restart |
| Commands affect a different scope than expected | Account/org commands need not honor repository context; explicit CLI options can override context | Inspect preview and command help before confirmation |
| Windows behavior is unverified | Process-group/selectors handling and CI target macOS/Linux | Use a supported environment |
| Layout feels cramped | Multi-pane Textual layout needs room | Enlarge terminal to around 120×40 or more |

No application error-history file, automatic retries, or rollback of completed
GitHub mutations is provided. See [the diagnostic runbook](runbooks/troubleshooting.md)
for failures and [testing](TESTING.md) for test limitations.
