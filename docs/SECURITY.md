# Security model

## Principals and trust boundaries

A local user controls the terminal, command text, working directory, and installed
GitHub CLI. GitHub CLI authenticates with its own configuration/environment and
applies GitHub authorization. Explorer does not create a credential store or
restrict commands to read-only operations. A confirmed command can change local
files, repositories, organizations, or account state.

The main boundaries are user input → Python argv, Python → installed `gh`/`git`, and
those programs → configured remotes or installed tools. Trusted `gh` and `git`
binaries on PATH are required. Aliases, extensions, Git hooks and credential
helpers may invoke shells or other programs independently.

## STRIDE review

| Threat | Mitigation and remaining boundary |
| --- | --- |
| Spoofing | Explicit command/context preview; authentication delegated to `gh`; PATH is trusted |
| Tampering | Shell-free argv; directory and repository validation; explicit execution confirmation; user commands may intentionally mutate data |
| Repudiation | No durable command audit trail; UI status/output are session-local |
| Information disclosure | No automatic output/credential persistence; literal Rich text; explicit clipboard copy; terminal and subprocess behavior are outside the app's retention guarantee |
| Denial of service | Captured output limit, help timeout, captured-mode timeout/cancel; terminal mode needs user intervention |
| Elevation of privilege | Runs with the user's permissions; confirmation is a UX boundary, not a sandbox |

## Secrets, input, and output

Do not store credentials in project files, examples, diagnostics, or workflow logs.
Use `gh auth login`; revoke/rotate a compromised credential with its issuer and
update the GitHub CLI configuration outside this repository. Explorer supplies no
credential rotation mechanism.

`shlex.split` parses command text; `shlex.join` previews and appends arguments.
Standalone shell operators are rejected. For GitHub CLI commands, the optional repository override accepts
`OWNER/REPO` or `HOST/OWNER/REPO`, not a URL. The working directory must exist. Direct Git ignores the repository override
and removes inherited `GH_REPO`; it uses normal Git remote/upstream configuration.
Quick actions require the same explicit confirmation as manually entered commands.
Command stdout/stderr is displayed as literal text rather than Rich markup.
Captured text and preview arguments may still contain private information; inspect
and sanitize them before copying or reporting a problem.

## Review checklist

- Does discovery invoke only local help, including when aliases shadow command names?
- Do all user-entered commands and settings mutations preserve confirmation, argv handling, and context?
- Are automatic repository reads limited to repo metadata, GET tree/blob requests, and local help?
- Are cancellation, timeout, process cleanup, and output bounds still effective?
- Do tests use fixtures instead of authenticated mutations?
- Do logs/indexes/package artifacts exclude credentials, private output, and local state?

## Reporting and incidents

Follow [security reporting](../.github/SECURITY.md) and the
[diagnostic runbook](runbooks/troubleshooting.md). There is no central error file,
remote telemetry, on-call service, or promised response SLA. The app makes no
compliance certification or data-residency claim; GitHub CLI decides where its
network requests go based on its configuration and the executed command.

## Embedded editor

Only a matching local checkout enables editing. Matching resolves the checkout's
GitHub identity without the selected repository override. Paths must remain inside
the checkout and cannot traverse symlinks or `.git`; only existing UTF-8 text files
up to 500 KB open in Vim. Remote previews never become local file contents.

Vim runs as literal argv in a PTY, with configuration/plugins, modelines, swap,
backups, persistent undo and viminfo disabled. Editor output stays in memory.
Explicit saves persist the selected file. Vim still has the user's privileges;
intentional Vim commands can access other paths or launch other programs. This
is an editor integration, not a sandbox. Vim handles write errors, on-disk changes
and unsaved buffer prompts. Explorer guards normal close and standalone Ctrl+Q;
forced process termination and embedding hosts remain outside those guards.

## Repository browsing and settings

Startup performs read-only repository discovery, local Git reads and PR/branch
requests. Remote-only files are read by blob SHA and displayed as literal text;
remote preview bytes are never written into a checkout. File contents and settings snapshots remain in memory.
Previews are limited to 500 KB. Truncated API output is rejected. All API reads use
explicit GET and the host resolved by `gh repo view`; Enterprise repositories retain
their host. Repository edit commands pin an explicit target and require confirmation.
Only selected flags are sent, including explicit false values. Visibility acceptance
is never added automatically. GitHub remains responsible for permissions and policy.
