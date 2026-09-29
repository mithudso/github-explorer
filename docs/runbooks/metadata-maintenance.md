# Refresh repository metadata

## Preconditions

Use a checkout with the uv environment installed. Review unrelated worktree
changes. Do not start semantic indexing, embeddings, or an Ollama process.

## Actions

1. Update architecture/component/operations descriptions to match source behavior.
2. Regenerate operations artifacts with
   `uv run python scripts/generate_ops_registry_doc.py`.
3. Regenerate navigation artifacts with `uv run python scripts/generate_repo_indexes.py --refresh`.
4. Run `uv run python scripts/rotate_workflow_logs.py` for a dry run when either
   workflow log approaches 200 KB. Close active editors and review the plan, then
   use `--apply` to archive old sections. The default retains the latest three
   sections per log and refuses editor markers; `--help` lists size/retention options.
5. Record the task, validation, and remaining work in the versioned workflow logs.
6. Regenerate navigation artifacts again after log edits or rotation; the census
   hashes workflow files even though it does not copy their contents.

## Verification

Run `uv run python scripts/generate_ops_registry_doc.py --check` and
`uv run python scripts/check_doc_indexes.py`. Inspect generated diffs for private
paths/content and run the project's normal checks before committing.

## Escalation

If an artifact is stale after generation, inspect its generator and source metadata
rather than patching JSON by hand. Record an unresolved generator defect with a
minimal fixture reproduction.
