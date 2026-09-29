# Development

## Prerequisites and setup

Use Python 3.11 or newer, `uv`, and a Git checkout. The lockfile supplies resolved
versions; the CI matrix exercises Python 3.11 and 3.14 on macOS and Linux.
Install GitHub CLI on PATH to run the app. Authenticate with `gh auth login` only
for the default repository file browser, settings reads, and commands that need GitHub access. Fixture tests require no account.

```sh
uv sync --locked
uv run github-explorer --cwd .
```

No `.env` file, service, database, watch server, or live reload is required. Restart
the app after source changes. The VS Code launch configuration uses the integrated
terminal; select the `.venv` interpreter created by uv.

## Checks

```sh
uv run pytest
uv run pytest tests/test_runner.py
uv run ruff check .
uv build
uv run python scripts/generate_ops_registry_doc.py --check
uv run python scripts/check_doc_indexes.py
```

No standalone type-checker or numeric coverage threshold is configured. See
[testing](TESTING.md) for behavioral priorities. CI runs checks on pushes and pull
requests. There is no automated publication/deployment workflow.

## Making a change

1. Read the relevant component and fixture tests; preserve unrelated edits.
2. Work on a focused branch. There is no enforced branch/commit naming scheme.
3. Put discovery changes in `catalog.py`, execution in `runner.py`, reusable UI in
   `panel.py`, and standalone behavior in `app.py` / `__main__.py`.
4. Add a regression test for changed behavior, using fake `gh` help or local
   fixture processes. Never mutate live GitHub state in tests.
5. Update relevant docs and the versioned `prompts.md` / `memory.md` logs.
6. For a release change, update `pyproject.toml`, `__init__.py`, `CHANGELOG.md`, and
   the project version in `uv.lock` together (`uv lock` refreshes the lockfile).
7. Regenerate metadata after file/module/operation changes:

   ```sh
   uv run python scripts/generate_ops_registry_doc.py
   uv run python scripts/generate_repo_indexes.py --refresh
   ```

8. Run the checks above, review the diff for private data, and commit only the
   task's files. [Contributing](../CONTRIBUTING.md) describes PR expectations.

## Environment

The application does not load `.env`; [.env.example](../.env.example) documents
inherited settings. `PATH` resolves `gh`. The repository field or `--repo` supplies
`GH_REPO`; a blank field removes inherited `GH_REPO` for execution. Captured mode
sets `GH_PROMPT_DISABLED=1`, `GH_PAGER=cat`, `PAGER=cat`, `NO_COLOR=1`, and removes
`GH_FORCE_TTY`. Help discovery sets the pager/color variables. Terminal mode retains
normal prompt/TTY settings. Authentication settings belong to GitHub CLI; do not
record tokens in this repository.

## Troubleshooting

If `gh` is missing, fix PATH and relaunch. If discovery fails, run `gh help reference`
and `gh --help` locally to isolate the CLI problem. If Run needs stdin or an editor,
use Terminal. If imports fail, rerun `uv sync --locked` and use `uv run` rather than
an unrelated Python environment. See [known issues](known-issues.md) and
[the diagnostic runbook](runbooks/troubleshooting.md).
