# Security model

## Principals and trust boundaries

A local user controls the terminal, command text, working directory, and installed
GitHub CLI. GitHub CLI authenticates with its own configuration/environment and
applies GitHub authorization. Explorer does not create a credential store or
restrict commands to read-only operations. A confirmed command can change local
files, repositories, organizations, or account state.

The main boundaries are user input → Python argv, Python → installed `gh`, and
`gh` → GitHub or installed extensions. A trusted `gh` binary on PATH is required.
Aliases and extensions may invoke shells or other programs independently.

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
Standalone shell operators are rejected. The optional repository override accepts
`OWNER/REPO` or `HOST/OWNER/REPO`, not a URL. The working directory must exist.
Command stdout/stderr is displayed as literal text rather than Rich markup.
Captured text and preview arguments may still contain private information; inspect
and sanitize them before copying or reporting a problem.

## Review checklist

- Does discovery invoke only local help, including when aliases shadow command names?
- Does every execution path preserve confirmation, argv handling, and context?
- Are cancellation, timeout, process cleanup, and output bounds still effective?
- Do tests use fixtures instead of authenticated mutations?
- Do logs/indexes/package artifacts exclude credentials, private output, and local state?

## Reporting and incidents

Follow [security reporting](../.github/SECURITY.md) and the
[diagnostic runbook](runbooks/troubleshooting.md). There is no central error file,
remote telemetry, on-call service, or promised response SLA. The app makes no
compliance certification or data-residency claim; GitHub CLI decides where its
network requests go based on its configuration and the executed command.
