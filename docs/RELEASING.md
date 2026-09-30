# Distribution and releases

The Python package remains the application. Homebrew installs it in a private
virtual environment. The npm package bundles the matching Python wheel and a
locked runtime requirements file; its two launchers use `uv tool run` with an
isolated cached environment, inherited terminal, and the caller's working directory.
Neither npm installation nor its launcher executes a shell installation script.
First launch needs network access to install Python dependencies; uv can download
a compatible Python when none is available. Subsequent launches reuse its cache.

## Release procedure

1. Update versions in `pyproject.toml`, `src/github_explorer/__init__.py` and
   `npm/package.json`; run `uv lock`. Update the changelog and workflow records.
2. Run `uv sync --locked`, `uv run pytest`, `uv run ruff check .` and
   `npm --prefix npm test`. Refresh and check the generated documentation.
3. Run `uv run python scripts/build_distributions.py`. It builds the wheel and
   source archive, stages an allowlisted npm payload, and generates Homebrew
   resources from the runtime lockfile with SHA-256 hashes. Do this after final
   source/document changes. Keep the generated formula with the exact archive
   it references; rebuilding a source archive can change its checksum.
4. Run `npm pack ./npm --pack-destination dist` and inspect its file list. Install
   the tarball into a temporary prefix and exercise both aliases, `--version`,
   and `--list-commands` from outside the checkout. Run `brew style`, install the
   formula from the tap, and run `brew test` / `brew audit`.
5. Commit project sources and the formula, push the release commit, tag it, and
   create a GitHub release containing the exact wheel, source archive, npm tarball
   and `SHA256SUMS`. Do not regenerate artifacts after recording their hashes.
6. Publish the formula to `mithudso/homebrew-tap`. Homebrew core is a separate
   submission with its own [acceptance policy](https://docs.brew.sh/Package-Acceptance-Policy).
   This young project currently uses the author's tap.
7. Sign in using `npm login` (never commit credentials), then run
   `npm publish dist/mitchphudson-github-explorer-VERSION.tgz --access public`.
   npm may require browser/2FA verification. Confirm the version and integrity
   through `npm view`, then install from the registry into a temporary prefix.

Use the scoped package name owned by the publishing account. The unscoped
`github-explorer` name belongs to another project. Both installed commands remain
`github-explorer` and `ghx`. npm requires Node.js 18+ and uv on PATH. Both channels
support macOS and Linux, and use the user's GitHub CLI authentication.

Release artifacts and npm staging files are ignored by Git. The GitHub release
is their durable distribution location. Do not publish logs, credentials, local
state or generated build directories as source files.

If npm resolves a parent project configuration, publish from a temporary directory
with an explicit user config and the absolute tarball path. Verify `npm whoami`
using that same directory and config. An ancestor .npmrc can override the user config.
