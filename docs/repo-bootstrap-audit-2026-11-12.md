# Bootstrap and code optimization audit — 2026-11-12

Release source: 0.4.3. Scope: the public Python/Textual application, npm launcher,
maintenance scripts, fixture tests, packaging, CI, contributor metadata and documentation.

## Coverage and method

- Reviewed all 30 final Python/CommonJS source and test files with separate per-file diagnostics. No file-count truncation.
- Applied C1–C3, S1–S5, P1–P2, M1–M4 and T1–T4. Repository-wide passes covered architecture, dependencies, tooling and test isolation.
- Established the baseline before fixes: 90 Python tests, 3 npm tests, Ruff, wheel/source builds and both metadata checks passed.
- New counterexample cases failed before implementation. Mutation checks rejected no-op Quit, missing host checks and captured-mode substitution for Terminal.
- Fixture tests are regression checks, with no reserved held-out benchmark. Empirical champion promotion and performance claims do not apply.
- The first blind gate found a release-input symlink leak. After one repair round, a second fresh-context gate covered all 18 passes and found no corroborated Medium+ defects. Its focused runner/workspace check passed 24 tests.

## Findings and corrections

| ID | Pass | Location | Severity | Finding | Correction |
| --- | --- | --- | --- | --- | --- |
| F01 | C1/P2 | [src/github_explorer/panel.py:622](../src/github_explorer/panel.py#L622) | High | Vim could open during command execution | Guard editor entry and command start. |
| F02 | C1/C3 | [src/github_explorer/runner.py:324](../src/github_explorer/runner.py#L324) | Medium | Checkout-root whitespace was stripped | Remove only the Git response terminator. |
| F03 | S1/S3 | [scripts/generate_repo_indexes.py:252](../scripts/generate_repo_indexes.py#L252) | Medium | Nested private workflow documents entered generated text | Exclude private document bodies by basename at every depth. |
| F04 | C1/S3 | [scripts/generate_repo_indexes.py:342](../scripts/generate_repo_indexes.py#L342) | Medium | Source links corrupted special characters | URL-encode refs and file paths. |
| F05 | C1/M4 | [scripts/generate_repo_indexes.py:595](../scripts/generate_repo_indexes.py#L595) | Medium | Foreign overview/index files could be overwritten | Require an owned manifest and explicit refresh before replacing any output. |
| F06 | C1/M4 | [scripts/generate_repo_indexes.py:310](../scripts/generate_repo_indexes.py#L310) | Medium | CI block and named-step commands were misreported | Parse workflow run values with safe YAML loading. |
| F07 | P2/S2 | [scripts/rotate_workflow_logs.py:56](../scripts/rotate_workflow_logs.py#L56) | High | Concurrent log changes could be replaced by a cached plan | Compare planned content before writes and replacement; require idle writers. |
| F08 | C1/C3 | [scripts/rotate_workflow_logs.py:38](../scripts/rotate_workflow_logs.py#L38) | Medium | Invalid fence closers changed rotation section boundaries | Require valid closing-fence suffix and indentation. |
| F09 | S2/S5 | [scripts/check_doc_indexes.py:35](../scripts/check_doc_indexes.py#L35) | Medium | Unreadable generated output escaped checker diagnostics | Return a path-specific error and normal refresh guidance. |
| F10 | S1/S3 | [scripts/build_distributions.py:58](../scripts/build_distributions.py#L58) | Medium | Unexpected staging files could enter public npm payload | Refuse foreign staging entries and enforce the prepack allowlist. |
| F11 | S1/S3 | [scripts/build_distributions.py:50](../scripts/build_distributions.py#L50) | Medium | Release output symlinks could redirect writes or deletions | Preflight output paths before any build or staging mutation. |
| F12 | C1/S3 | [npm/check-package.cjs:17](../npm/check-package.cjs#L17) | Medium | Directories or symlinks could satisfy package completeness checks | Require regular payload files, real parent directories and the launcher. |
| F13 | S2/S3 | [src/github_explorer/__main__.py:29](../src/github_explorer/__main__.py#L29) | Medium | Unknown home-directory paths raised uncaught errors | Report invalid CLI/context paths before executable lookup. |
| F14 | T1 | [tests/test_workspace.py:117](../tests/test_workspace.py#L117) | Medium | Checkout matcher tests did not exercise host rejection | Assert same-name/different-host rejection and valid matching. |
| F15 | T1 | [tests/test_cli.py:90](../tests/test_cli.py#L90) | Medium | Quit assertion did not prove shutdown | Assert the public exit-code transition; a no-op mutant fails. |
| F16 | T1 | [tests/test_panel.py:96](../tests/test_panel.py#L96) | Medium | Terminal-button assertion did not prove terminal delegation | Assert suspension, exact interactive call and no extra captured call. |
| F17 | S4/T1 | [tests/conftest.py:10](../tests/conftest.py#L10) | Medium | A UI error-path test used installed gh settings help | Provide fixture settings and reject accidental help subprocess calls. |
| F18 | M4 | [scripts/generate_repo_indexes.py:410](../scripts/generate_repo_indexes.py#L410) | Medium | Executable inventory omitted the npm package | Statically inventory npm launchers and scripts; refresh file roles. |

| F19 | S1/S3 | [scripts/build_distributions.py:16](../scripts/build_distributions.py#L16) | Medium | Source documentation symlinks could publish outside file contents | Reject symlinked metadata, documentation and source-archive inputs before building. |

## Bootstrap manifest

All applicable workflow, editor, security, installation, architecture, testing and
operations files are present. The new [project wiki](wiki/README.md) links maintained
commands, scripts, reference material and the existing design constraints. Contributor
commands now include npm tests and distribution guards; `.node-version` supplies the
CI Node major version. The Python lockfile includes development-only PyYAML for static
workflow extraction. Runtime dependencies remain unchanged.

Existing Python operation metadata replaces service-specific JavaScript paths. The
app owns no server, datastore, MCP runtime or persistent command log. Human remediation
guidance and ephemeral status remain appropriate; automatic replay remains disabled.
No semantic indexer, embedding process, watcher, new local agent, or service was added.
The static source dossier is regenerated from its maintained Python generator.
Historical bootstrap reports remain unchanged and retain their dated context.

## Validation

| Check | Result |
| --- | --- |
| `uv sync --locked` | Pass |
| `uv run pytest` | 139 passed |
| `uv run ruff check .` | Pass |
| `uv build` | Pass; wheel and source archive |
| `npm --prefix npm test` | 11 passed |
| Operation metadata / source-index checks | Operation metadata passes; static indexes refreshed before commit |
| Distribution staging, prepack and isolated installation | Pass; exactly 7 package files; both aliases report 0.4.3 and discover 236 local help commands |
| Installed dependency audit | No known vulnerabilities reported on this date |

## Convergence

| Iteration | Critical | High | Medium | Outcome |
| --- | ---: | ---: | ---: | --- |
| 1: runtime and maintenance | 0 | 2 | 11 | Corrected with counterexamples |
| 2: coverage and metadata | 0 | 0 | 5 | Corrected with fixture/mutation checks |
| 3: first blind gate | 0 | 0 | 1 | Reproduced release-input leak; repair required |
| 4: repaired final candidate | 0 | 0 | 0 | Independent gate passed; CLEAN |

Summary: 4 iterations · 18 active passes · standard profile · final C/H/M: 0/0/0 · Verify: PASS · Status: CLEAN. All 19 findings were corrected.

## Limits and rollback

No live GitHub mutation was used for app verification. Live discovery read only local
help. Real Vim tests edit disposable files. Interactive terminal behavior, Windows
and a real Homebrew install remain outside this run. Distribution packages were built
and installed locally; version 0.4.3 was not published to a registry or release.
The checked-in Homebrew formula continues to identify the last published 0.4.2 archive.
Rotation requires idle log writers; content comparisons detect changes but do not
serialize unrelated external writers. Do not rotate an actively edited log.

Rollback uses a reviewed revert of this PR. Runtime command cancellation cannot undo
completed Git/GitHub actions. Generated artifacts must be refreshed from their source
after any revert. Local pre-write snapshots are retained outside the public repository.
