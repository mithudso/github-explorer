# Integrations and assumptions

## Runtime boundaries

| Integration | Calling code | Data and authentication |
| --- | --- | --- |
| Installed `gh` help | `catalog.help_text`, `catalog.load_catalog` | Local help text out; installed binary resolved through PATH; no Explorer API client |
| Captured `gh`/`git` command | `runner.CommandRunner.run` | Explicit argv/cwd/env in; combined stdout/stderr and exit status out; the selected executable owns auth/network behavior |
| Terminal `gh`/`git` command | `runner.run_interactive` | Explicit argv/cwd/env in; inherited terminal streams; the selected executable owns auth/network behavior |
| Embedded Vim | `runner.vim_command`, `panel.VimEditor`, textual-tty/bittty | Local text path and literal argv; PTY output in memory; saves write the checkout |
| Host terminal / clipboard | `panel.GitHubPanel` via Textual | Explicit copy of last captured result; terminal capabilities determine clipboard behavior |

Explorer has no hardcoded GitHub API base URL or direct HTTP SDK. The installed
CLI, requested command, host override, and its configuration decide endpoints.
[External calls](external-calls.md) and [operations registry](operations-registry.json)
record the subprocess boundaries.

## Assumptions

- PATH selects trusted `gh` and `git`; aliases/extensions/hooks may execute local tools.
  Direct Git uses the checkout and configured remotes; GH_REPO does not redirect it.
- Help reference uses Markdown headings and root help uses labeled command sections.
  Future CLI formatting changes may require parser updates.
- The current directory is an existing local directory. A repo override is
  `OWNER/REPO` or `HOST/OWNER/REPO`; it does not restrict account-wide commands.
- Shell operators/pipelines are unsupported in the app; use native CLI arguments.
- Captured commands do not need stdin. Interactive commands use Terminal mode.
- Captured output is limited in memory and not written by the app. Commands may
  themselves create files, update checkouts, or store credentials.
- macOS/Linux are tested; terminal-mode embedding requires `App.suspend()`.

## Development services

GitHub Actions runs CI; Dependabot configuration requests dependency updates for
uv and GitHub Actions. These are repository maintenance integrations, not runtime
services. uv downloads dependencies during setup/build as needed. There is no
production/dev server split. Authentication and environment handling are documented
in [development](DEVELOPMENT.md). Index generation is local and lexical; no Ollama,
embedding process, or watcher is required or enabled.

## Default repository reads

The file browser resolves GitHub identity and checks the local checkout identity
without an override. Matching checkouts use git ls-files; other contexts use remote
default-branch trees through explicit GET. Status reads local Git every two seconds
and paginated open PRs/branches every minute. Directory-by-directory traversal may take multiple requests for
large repositories. File previews use immutable blob SHAs and a 500 KB limit.
Settings use the repository REST response for known current values and local
`gh repo edit --help` for the complete editable option set. GitHub permissions,
repository type and organization policy can restrict changes or hide current values.
