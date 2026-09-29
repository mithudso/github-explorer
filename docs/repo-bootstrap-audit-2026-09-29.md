# Repository bootstrap audit — 2026-09-29

Release: 0.1.1. Scope: the public Python/Textual application, tests, workflow
metadata, contributor documentation, and local maintenance tooling. This resumes an
interrupted baseline audit; the only pre-existing edits were its workflow records.

## Outcome

The applicable local-application baseline is implemented. Full service-contract
compliance is not claimed: this app has no server, datastore, persistent command log,
or MCP runtime. The final validation record is in `memory.md`.

## Findings and resolution

| Finding | Severity | Resolution / evidence |
| --- | --- | --- |
| Missing contributor, architecture, security and operational docs | Major | Added docs suite and linked entry points; paths checked locally |
| Missing issue/PR templates, ownership, dependency updates, editor settings | Medium | Added public project-specific metadata |
| No generated-index or operation-document drift gate | Medium | Python generators/checker plus fixture tests and CI steps |
| Cancelled catalog load could replace a newer result | High | Worker cancellation checked before delivery and UI update; controlled overlapping-load test |
| Incomplete UTF-8 output tail disappeared | Medium | Finalize decoder at EOF; subprocess regression fixture |
| Nonfinite runner timeout allowed an unbounded child | Medium | Reject NaN/infinity before process creation; negative-effect assertions |
| Help timeout escaped CLI error handling | Medium | Translate timeout into user-facing error; CLI exit assertion |
| Generated output could follow a symlink | Medium | Preflight output paths; refuse unsafe targets before writes; maintenance fixtures |
| Remote URL query/fragment could enter public generated docs | Medium | Strip URL query/fragment; credential regression fixture |
| Tracked source directory replaced by a symlink could expose outside content | Medium | Reject symlinked ancestors and resolved paths outside the repo; isolated tracked-directory regression |
| Rotation could delete a pre-existing recovery temporary file | Medium | Only clean up a temporary file created by this invocation; preservation fixture |
| Output limit label said MB although measured in characters | Minor | Label corrected to two million characters |

## Applicability decisions

- Keep Python tooling; JavaScript registry paths and Node version pins do not apply.
- Inventory runtime subprocess and clipboard boundaries in `operations.py` and
  `docs/external-calls.md`. The declarative registry never runs or retries operations.
- Preserve transient command output. A central persistent JSONL sink would conflict
  with the existing project privacy rule. Human remediation guidance replaces unsafe
  automatic replay of arbitrary GitHub actions.
- Explicitly declare no application datastore, MCP tools, HTTP routes, local agents,
  native host, browser extension, deployment daemon, or service dashboard.
- Do not install or run semantic indexers, watchers, Ollama, or keyword pipelines.
  The static dossier is repository documentation, not an embedding service.
- Do not create repository-local agent/skill copies without a real task for them.
  No `docs/*-context.md` skill sources exist. Existing user tooling is outside the repo.
- Preserve LICENSE and NOTICE.md. Generated build outputs and local state stay ignored.
- No response SLA, numeric test-coverage threshold, or Windows support is invented.

## Review coverage

Code-deep-optimizer covered correctness/contracts/adversarial tests (C1–C3),
security/errors/validation/portability/observability (S1–S5), performance/concurrency
(P1–P2), maintainability/duplication/architecture/documentation (M1–M4), and
behavioral tests/dependencies/tooling/test speed (T1–T4). The package has seven
small modules with no service or database layering. No API migration was required.
Existing fixture tests are a regression gate, not a held-out benchmark; no empirical
optimization score or performance gain is claimed.

An independent review inspected core fixes and maintenance writes. It identified
output-symlink and remote URL handling problems before final validation. Both were
routed back to the corresponding generator. The convergence pass checks these fixes
and regenerates metadata after documentation changes.

## Dependencies and tooling

`uv.lock` is committed. `uv pip list --outdated` returned no outdated installed
packages during this run. `pip-audit` reported no known vulnerabilities in the
installed dependencies; the local `github-explorer` package is not a published PyPI
audit target and was skipped. These results are a dated observation, not a guarantee.
CI retains macOS/Linux and Python 3.11/3.14 matrix checks. No new runtime dependency
was added by the bootstrap. The `uv` Dependabot ecosystem setting was checked
against [Astral documentation](https://docs.astral.sh/uv/guides/integration/dependabot/).
`MANIFEST.in` includes maintenance scripts and registry fixtures so the source
archive can run the test suite.

## Remaining scope

Semantic indexing remains paused. Interactive terminal behavior still requires a
real-terminal smoke check; fixture tests cover delegation. This session runs local
checks; remote GitHub Actions results require pushing the commit. The app's known
limitations are recorded in [known-issues.md](known-issues.md).

## Final continuation review

The resumed run verified the existing uncommitted bootstrap and found one additional
source-census privacy issue: a tracked directory replaced by an external symlink
could still supply cached descendant paths. The generator now excludes symlinked
ancestors and paths outside the repository. A regression verifies exclusion and
absence of outside content from every generated artifact. Independent review
confirmed the fix. The final workflow-log edit requires index regeneration before
commit; the final results belong in `memory.md`.
