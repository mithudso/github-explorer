# Workflow log archive

`scripts/rotate_workflow_logs.py` moves older versioned sections from oversized
`prompts.md` and `memory.md` logs here. Consult its `--help` before use. Keep the
latest continuation context in the root logs and retain archive links there.
Rotation refuses active editor swap files to avoid losing an in-progress edit.

Archive only public project history. Never move private local state or command
output into this tracked directory merely because it is called an archive.
