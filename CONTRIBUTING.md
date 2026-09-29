# Contributing

Read [development](docs/DEVELOPMENT.md), [architecture](docs/ARCHITECTURE.md), and
[AGENTS.md](AGENTS.md). Open an issue for a substantial behavior change before
preparing a patch when design feedback would help.

Create a focused branch, use fixture commands in tests, and include a behavior
regression test for a bug fix. Run `uv sync --locked`, `uv run pytest`,
`uv run ruff check .`, and `uv build`. Run the documentation checks listed in
[development](docs/DEVELOPMENT.md) when metadata or paths change.

Describe the trigger, resulting behavior, validation, risks, and rollback in a PR.
Preserve unrelated edits. Update `prompts.md`, `memory.md`, and relevant docs;
increment their versions/deltas and the release version when appropriate.
Retain attribution in `LICENSE` and `NOTICE.md`. Do not commit credentials,
command output, local state, or private source-project data.

Follow the [code of conduct](CODE_OF_CONDUCT.md). Report vulnerabilities using
[the security reporting instructions](.github/SECURITY.md).
