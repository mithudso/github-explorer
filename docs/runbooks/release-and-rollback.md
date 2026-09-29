# Prepare a release or roll back an installation

## Preconditions

Work from a reviewed checkout and preserve unrelated changes. Publication is a
maintainer action; the repository has no automated release workflow.

## Actions

1. Update the package version in `pyproject.toml` and `__init__.py`, refresh
   `uv.lock`, and record the change in `CHANGELOG.md`.
2. Update workflow logs and affected docs; regenerate operations and file indexes.
3. Run `uv sync --locked`, `uv run pytest`, `uv run ruff check .`, and `uv build`.
4. Run the metadata checks in [development](../DEVELOPMENT.md).
5. Review the staged diff for local state, credentials, and private output, then
   commit only the intended files. Retain `LICENSE` and `NOTICE.md` in packages.
6. If rolling back a local tool install, reinstall a known reviewed Git revision
   using `uv tool install --force git+https://github.com/mithudso/github-explorer.git@REVISION`,
   replacing `REVISION` with the actual revision. Do not guess a release tag.

## Verification

Check `github-explorer --version`, `--help`, and local catalog loading. For a
checkout, prefix app commands with `uv run`. An application rollback does not undo
GitHub operations already completed by commands run through the app.

## Escalation

Open a sanitized issue for a reproducible regression. For a security defect,
follow [security reporting](../../.github/SECURITY.md) before public disclosure.
