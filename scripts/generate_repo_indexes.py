"""Generate portable static repository indexes without importing application code."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import tomllib
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = "crawl-repo-to-llms"
SKILL_VERSION = "1.2.0"
SCHEMA_VERSION = 1
OUTPUTS = (
    "docs/high_signal_file_index.json", "docs/codebase-overview.md",
    *(f"docs/llms/{name}" for name in (
        "llms.txt", "llms-full.txt", "llms-small.txt", "llms-facts.txt", "llms-filemap.txt",
        "llms-indexes.txt", "llms-infra.txt", "llms-history.txt", "llms-executable.txt",
        "filemap.json", "manifest.json",
    )),
)
EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build",
    "node_modules", ".stele", ".remember", ".codex", ".claude", ".idea",
}
PRIVATE_DOCS = {"AGENTS.md", "CLAUDE.md", "prompts.md", "memory.md"}
# Curated from direct source review; refresh these explanations when their seams change.
# Tuple fields: purpose, why, when, reading entrypoints, source dependencies, test gate.
REVIEWED = {
    "src/github_explorer/__init__.py": (
        "Expose GitHubExplorer, GitHubPanel and the package version.",
        "Consumers import the reusable screen and standalone host from this facade.",
        "Changing public imports or the release version.", "__all__, __version__",
        ["src/github_explorer/app.py", "src/github_explorer/panel.py"], "tests/test_cli.py"),
    "src/github_explorer/__main__.py": (
        "Parse launch options, validate repository context and select JSON catalog or TUI mode.",
        "Both console-script aliases and python -m use this entrypoint.",
        "Changing CLI flags, startup validation or error exit behavior.", "main",
        ["src/github_explorer/__init__.py", "src/github_explorer/app.py", "src/github_explorer/catalog.py", "src/github_explorer/runner.py"], "tests/test_cli.py"),
    "src/github_explorer/app.py": (
        "Host GitHubPanel in a standalone Textual application.",
        "Keeping the host separate allows other Textual apps to embed the panel.",
        "Changing standalone startup, branding or exit behavior.", "GitHubExplorer.__init__, on_mount",
        ["src/github_explorer/panel.py"], "tests/test_cli.py"),
    "src/github_explorer/catalog.py": (
        "Parse local gh help, derive repository setting arguments and define curated Git shortcuts.",
        "The UI needs searchable local commands without executing aliases or extensions.",
        "Changing help parsing, external-command classification or discovery errors.",
        "load_catalog → help_text → parse_catalog; flags_from_help; QUICK_ACTIONS; git_commands", [], "tests/test_catalog.py"),
    "src/github_explorer/runner.py": (
        "Prepare shell-free argv, run child processes and read GitHub repository metadata, trees and blobs.",
        "Execution shares repository context, bounded capture, cancellation and timeout semantics.",
        "Changing argument handling, subprocess cleanup, output decoding or environment isolation.",
        "prepare → Invocation.environment → CommandRunner.run; run_interactive",
        ["src/github_explorer/catalog.py"], "tests/test_runner.py"),
    "src/github_explorer/panel.py": (
        "Compose file browsing, CLI controls, shortcuts, directional navigation, settings and confirmation.",
        "One screen connects discovery and execution while keeping explicit user confirmation.",
        "Changing arrow navigation, quick actions, asynchronous refresh, previews or host integration.",
        "GitHubPanel.compose → load_commands/loaded → request_run → start_command/execute; CommandConfirm",
        ["src/github_explorer/catalog.py", "src/github_explorer/runner.py"], "tests/test_panel.py"),
    "src/github_explorer/operations.py": (
        "Declare runtime operation metadata records and return independent copies.",
        "Maintainers can document behavior and remediation without triggering discovery or execution.",
        "Changing the public operation inventory, source anchors or remediation guidance.",
        "OPERATIONS; list_operations; get_operation",
        [], "tests/test_maintenance.py"),
    "scripts/generate_ops_registry_doc.py": (
        "Parse OPERATIONS with AST and generate the operations registry and empty tool inventory.",
        "Published operation metadata must match source without importing the application.",
        "Changing registry schema, generated metadata or drift checking.", "render; main --check",
        ["src/github_explorer/operations.py"], "tests/test_maintenance.py"),
    "scripts/rotate_workflow_logs.py": (
        "Plan or archive older prompt and memory sections while retaining current context.",
        "Long workflow logs need bounded active files without losing earlier records.",
        "Changing archive thresholds, section parsing or safeguards around writes.",
        "plan_rotation → rotate → main; --apply enables writes",
        ["prompts.md", "memory.md"], "tests/test_maintenance.py"),
    "scripts/generate_repo_indexes.py": (
        "Generate static file indexes and the provenance-tagged repository dossier.",
        "A portable source map helps maintainers locate implementation and operating details.",
        "Changing census exclusions, file cards, parser extraction or generated documentation.",
        "census → code_inventory → render → write; REVIEWED holds curated explanations",
        ["pyproject.toml"], "tests/test_doc_indexes.py"),
    "scripts/check_doc_indexes.py": (
        "Compare the current source census and regenerated contents with committed indexes.",
        "Missing, changed or deleted sources must make stale documentation visible in CI.",
        "Changing drift detection, missing-output diagnostics or snapshot handling.", "check; main",
        ["scripts/generate_repo_indexes.py"], "tests/test_doc_indexes.py"),
    "tests/conftest.py": (
        "Provide network-free repository fixtures for UI tests.",
        "Automatic startup reads must never access a real account in tests.",
        "Changing shared UI repository fixtures.", "ui_repository",
        ["src/github_explorer/runner.py"], "tests/test_repository_panel.py"),
    "tests/test_repository.py": (
        "Verify repository identity, trees, previews, read failures and selected setting arguments.",
        "Read requests and settings argv need exact host/context and side-effect boundaries.",
        "Changing repository read helpers or setting discovery.", "FixtureRunner; repository",
        ["src/github_explorer/runner.py", "src/github_explorer/catalog.py"], "tests/test_repository.py"),
    "tests/test_repository_panel.py": (
        "Exercise default file browsing, settings confirmation and stale repository reads.",
        "User actions must preserve the resolved target and cancel without mutations.",
        "Changing files and settings UI or worker lifecycle.", "test_settings_current_values_cancel_and_confirm_exact_changes",
        ["src/github_explorer/panel.py"], "tests/test_repository_panel.py"),
    "tests/test_catalog.py": (
        "Test nested help parsing, alias classification, flags and the built-in-only discovery calls.",
        "Fixtures enforce discovery without executing discovered commands.",
        "Changing catalog parsers or discovery subprocess arguments.", "REFERENCE; test_loading_uses_only_builtin_help_commands",
        ["src/github_explorer/catalog.py"], "tests/test_catalog.py"),
    "tests/test_cli.py": (
        "Test CLI help/version, validation, JSON export, timeout handling and standalone hosting.",
        "CLI modes must select the correct behavior and preserve useful error exits.",
        "Changing startup options, errors, JSON shape or standalone screen integration.", "test_catalog_export_never_starts_tui; test_standalone_host_branding_context_and_quit",
        ["src/github_explorer/__main__.py", "src/github_explorer/app.py"], "tests/test_cli.py"),
    "tests/test_runner.py": (
        "Exercise literal argv, context, child exit status, cancellation, timeout and UTF-8 capture.",
        "Fixture Python children verify process behavior without GitHub side effects.",
        "Changing process execution, environment controls or bounded output handling.", "invocation; test_cancel_timeout_and_output_limit; test_incomplete_utf8_is_replaced_at_eof",
        ["src/github_explorer/runner.py"], "tests/test_runner.py"),
    "tests/test_shortcuts.py": (
        "Verify all twelve common command buttons and hotkeys, confirmations and responsive layout.",
        "Git and GitHub shortcuts must retain explicit execution and the correct context.",
        "Changing quick commands, hotkeys, busy guards or Git menu entries.",
        "test_button_and_hotkey_preview_cancel_and_execute; test_shortcut_bar_fits_and_resizes",
        ["src/github_explorer/catalog.py", "src/github_explorer/panel.py", "src/github_explorer/runner.py"], "tests/test_shortcuts.py"),
    "tests/test_navigation.py": (
        "Verify tree expansion, spatial arrow focus, native dropdowns and text editing.",
        "Arrow navigation must not activate commands or discard native editing behavior.",
        "Changing navigation in the panel, settings or confirmations.",
        "test_tree_arrows_expand_walk_collapse_without_selecting; test_spatial_buttons_fields_and_dropdown",
        ["src/github_explorer/panel.py"], "tests/test_navigation.py"),
    "tests/test_panel.py": (
        "Exercise embedded UI confirmation, argument editing, capture, clipboard, stopping and catalog races.",
        "Textual pilots verify user actions before mocked command execution.",
        "Changing screen events, confirmation boundaries or threaded completion callbacks.", "Host; test_embed_catalog_flags_preview_run_and_return; test_reload_ignores_cancelled_catalog_result",
        ["src/github_explorer/panel.py", "src/github_explorer/catalog.py", "src/github_explorer/runner.py"], "tests/test_panel.py"),
    "tests/test_maintenance.py": (
        "Test archival preservation and refusal, fenced headings, copied metadata and generated registries.",
        "Maintenance must preserve workflow content and keep public metadata synchronized.",
        "Changing log rotation or operation registry generation.", "script; test_rotation_preserves_all_sections_and_defaults_to_dry_run",
        ["scripts/rotate_workflow_logs.py", "scripts/generate_ops_registry_doc.py", "src/github_explorer/operations.py"], "tests/test_maintenance.py"),
    "tests/test_doc_indexes.py": (
        "Test deterministic generation, stale sources, file deletion/addition, exclusions and collisions.",
        "Fixture repositories check index correctness without application execution.",
        "Changing source census, generated dossier contracts or public-data guards.", "repo; test_generation_is_deterministic_and_does_not_index_its_outputs",
        ["scripts/generate_repo_indexes.py", "scripts/check_doc_indexes.py"], "tests/test_doc_indexes.py"),
}


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True,
    ).stdout.rstrip("\n")


def included(path: str) -> bool:
    parts = Path(path).parts
    return not (
        path in OUTPUTS or path.startswith("docs/llms/")
        or any(p in EXCLUDED_PARTS or p.endswith(".egg-info") for p in parts)
        or (Path(path).name.startswith(".env") and Path(path).name != ".env.example")
        or Path(path).suffix in {".pyc", ".pem", ".key", ".sqlite", ".db", ".log"}
        or Path(path).name in {".DS_Store", "credentials.json"}
    )


def census(root: Path) -> list[str]:
    """Include tracked and nonignored additions without traversing source symlinks."""
    paths = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")

    def safe_source(path: str) -> bool:
        source = root / path
        # Cached paths survive replacing a tracked directory with a symlink.
        # Reject every component before reading content or even its file size.
        for component in (source, *source.parents):
            if component == root:
                break
            if component.is_symlink():
                return False
        return source.is_file() and source.resolve().is_relative_to(root.resolve())

    return sorted({
        p for p in paths.split("\0") if p and included(p)
        and safe_source(p)
    })


def role(path: str) -> str:
    if path.startswith(".vscode/") or Path(path).name == ".env.example":
        return "config"
    if path.startswith("tests/"):
        return "test"
    if path.startswith(".github/workflows/"):
        return "infra"
    if path.startswith(".github/"):
        return "docs"
    if path.startswith("scripts/"):
        return "script"
    if path.endswith("__main__.py"):
        return "entrypoint"
    if path.startswith("src/"):
        return "library"
    if path.startswith("docs/") or path.endswith(".md"):
        return "docs"
    return "config" if path.endswith((".toml", ".lock")) else "meta"


def importance(path: str) -> str:
    if path in {"pyproject.toml", "src/github_explorer/__main__.py"}:
        return "critical"
    if path.startswith(("src/", ".github/workflows/")) or path == "README.md":
        return "high"
    return "peripheral" if role(path) in {"test", "script"} else "normal"


def read_public(root: Path, path: str) -> str:
    if path in PRIVATE_DOCS or Path(path).name == ".env.example" or path.startswith("docs/archive/"):
        return ""
    try:
        return (root / path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def safe_remote(raw: str) -> str:
    """Publish only an unauthenticated GitHub HTTPS repository URL."""
    raw = raw.removesuffix(".git")
    if raw.startswith("git@github.com:"):
        raw = "https://github.com/" + raw.split(":", 1)[1]
    parsed = urlsplit(raw)
    if parsed.scheme == "https" and parsed.hostname == "github.com" and not parsed.username:
        if re.fullmatch(r"/[\w.-]+/[\w.-]+", parsed.path):
            return f"https://github.com{parsed.path.removesuffix('.git')}"
    return "no-public-remote"


def snapshot(root: Path) -> dict:
    try:
        remote = safe_remote(git(root, "remote", "get-url", "origin"))
    except subprocess.CalledProcessError:
        remote = "no-public-remote"
    return {
        "source": ".", "remote": remote, "commit": git(root, "rev-parse", "HEAD"),
        "branch": git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "generated_at": date.today().isoformat(),
        "dirty": any(
            included(line[3:])
            for line in git(root, "status", "--porcelain", "--untracked-files=all").splitlines()
        ),
        "history": git(root, "log", "-200", "--format=%h %ad %s", "--date=short").splitlines(),
    }


def code_inventory(path: str, source: str) -> dict:
    """Parse declarations and argument definitions; do not import or execute them."""
    tree = ast.parse(source)
    options = []
    symbols = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_argument":
                options.append({
                    "definition": ast.get_source_segment(source, node),
                    "source": f"{path}:{node.lineno}",
                })
    return {"symbols": symbols, "options": options, "description": ast.get_docstring(tree)}


def json_text(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def render(root: Path, metadata: dict | None = None) -> dict[str, str]:
    metadata = metadata or snapshot(root)
    paths = census(root)
    sources = {p: read_public(root, p) for p in paths}
    code = {p: code_inventory(p, sources[p]) for p in paths if p.endswith(".py")}
    project = tomllib.loads(sources.get("pyproject.toml", "")).get("project", {})
    cards = []
    for path in paths:
        data = (root / path).read_bytes()
        cards.append({
            "path": path, "role": role(path), "importance": importance(path),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "depth": "shallow",
            "purpose": f"{role(path).capitalize()} file; semantic purpose requires source review.",
            "provenance": "[asserted]", "symbols": code.get(path, {}).get("symbols", []),
            "link": (f"{metadata['remote']}/blob/{metadata['branch']}/{path}"
                     if metadata["remote"] != "no-public-remote" else path),
        })
        card = cards[-1]
        if path in REVIEWED:
            purpose, why, when, reading, dependencies, gate = REVIEWED[path]
            card.update({
                "depth": "deep-read", "purpose": purpose, "why": why, "when": when,
                "how_to_read": reading,
                "how_to_edit": f"Run uv run pytest {gate}; full gates: uv run pytest, uv run ruff check ., uv build.",
                "depends_on": [p for p in dependencies if p in paths],
                "provenance": f"[src: {path}]",
                "edit_provenance": f"[src: README.md#development; {gate}, asserted-by-test]",
            })
    for card in cards:
        if card["depth"] == "deep-read":
            card["depended_on_by"] = [
                other["path"] for other in cards if card["path"] in other.get("depends_on", [])
            ]
    deep = sum(c["depth"] == "deep-read" for c in cards)
    shallow = len(cards) - deep
    manifest = {
        "generator": GENERATOR, "skill_version": SKILL_VERSION, "schema_version": SCHEMA_VERSION,
        **metadata, "census": {"enumerated": len(cards), "deep_read": deep, "shallow": shallow},
        "files": paths, "outputs": list(OUTPUTS),
        "counts_by_role": dict(sorted(Counter(c["role"] for c in cards).items())),
        "counts_by_importance": dict(sorted(Counter(c["importance"] for c in cards).items())),
        "budget_used": deep, "deferred_paths": [c["path"] for c in cards if c["depth"] == "shallow"],
        "scope": "Whole public file census; source, scripts and tests reviewed; other cards shallow.",
        "exclusions": ["ignored, private, build/cache files and symlinks", *sorted(EXCLUDED_PARTS),
                       "docs/llms/**", "docs/high_signal_file_index.json", "docs/codebase-overview.md"],
        "content_not_condensed": [*sorted(PRIVATE_DOCS), ".env.example"],
        "redactions": [], "index_probes": "disabled", "generated_output_self_indexing": False,
    }
    header_suffix = (
        f"> Source: . · {metadata['remote']} @ {metadata['commit'][:7]}"
        f"{' dirty' if metadata['dirty'] else ''}\n"
        f"> Generated: {metadata['generated_at']} by {GENERATOR} v{SKILL_VERSION}\n"
        f"> Census: {len(cards)} enumerated / {deep} deep-read / {shallow} shallow"
        " · partial: remaining metadata cards shallow; no index probes\n\n"
    )

    def document(title: str, body: list[str]) -> str:
        return f"# github-explorer — {title}\n{header_suffix}" + "\n".join(body) + "\n"

    facts = [
        f"Package: {project.get('name', 'unknown')}; version: {project.get('version', 'unknown')}. [src: pyproject.toml]",
        f"Purpose: {project.get('description', 'not declared')}. [src: pyproject.toml]",
        f"Requires Python {project.get('requires-python', 'not declared')}. [src: pyproject.toml]",
        f"Runtime dependencies: {', '.join(project.get('dependencies', []))}. [src: pyproject.toml]",
    ]
    for path, info in code.items():
        if info["description"]:
            facts.append(f"{path}: {' '.join(info['description'].split())} [src: {path}]")
    commands = []
    for name, target in project.get("scripts", {}).items():
        commands.append(f"`{name}` → `{target}`. [src: pyproject.toml#project.scripts]")
    commands.append("`python -m github_explorer` dispatches the package entrypoint. [src: src/github_explorer/__main__.py]")
    for path in paths:
        if path.startswith("scripts/") and path.endswith(".py"):
            commands.append(f"`python {path}`; inspect its options below before use. [src: {path}]")
    ci_commands = []
    for path in paths:
        if path.startswith(".github/workflows/"):
            ci_commands.extend(
                f"`{m.group(1)}`. [src: {path}]"
                for m in re.finditer(r"^\s*- run: (.+)$", sources[path], re.M)
            )
    options = []
    for path, info in code.items():
        for option in info["options"]:
            # Keep the exact call segment, including source newlines, in a code block.
            options.extend([f"Parser definition in {path}. [src: {option['source']}]",
                            "```python", option["definition"], "```"])
    env = []
    for path, source in sources.items():
        if path.startswith("src/") and path.endswith(".py"):
            names = sorted(set(re.findall(r"\b(?:GH_[A-Z_]+|PAGER|NO_COLOR)\b", source)))
            if names:
                env.append(f"{path} references environment names: {', '.join(names)}. [src: {path}]")
    executable = ["## Entrypoints", *commands, "", "## CI commands", *ci_commands, "",
                  "## Options (exact parser call sites)", *options, "", "## Environment", *env,
                  "The child process inherits the caller's environment; inherited credentials are not enumerated or persisted by this generator. [src: src/github_explorer/runner.py]",
                  "GH_REPO is cleared, then set from a nonempty selected repository only for gh; direct Git uses the local checkout configuration. [src: src/github_explorer/runner.py#Invocation.environment]",
                  "Captured mode sets GH_PROMPT_DISABLED=1, GH_PAGER=cat, PAGER=cat, NO_COLOR=1 and removes GH_FORCE_TTY. Interactive mode retains normal prompt behavior. [src: src/github_explorer/runner.py#Invocation.environment]",
                  "Catalog help sets GH_PAGER=cat, PAGER=cat and NO_COLOR=1. [src: src/github_explorer/catalog.py#help_text]",
                  "", "## Execution contracts",
                  "Application commands require the installed gh executable and an existing working directory; --repo must have OWNER/REPO or HOST/OWNER/REPO shape. [src: src/github_explorer/__main__.py]",
                  "--list-commands prints a JSON catalog; normal launch opens the Textual UI. [src: src/github_explorer/__main__.py]",
                  "Captured command output is retained in memory; Terminal mode uses the attached terminal. Child commands may change GitHub state after explicit execution. [src: src/github_explorer/runner.py; README.md#execution-behavior]",
                  "Application command options include argparse's implicit -h/--help; explicit options are copied above. [src: src/github_explorer/__main__.py]",
                  "The application has no persistent configuration file of its own; gh uses its existing authentication and configuration. [src: README.md#install-and-run; src/github_explorer/__main__.py]",
                  "Successful CLI completion returns 0; caught OSError/ValueError failures exit 1 with Error on stderr; argparse rejects invalid input. [src: src/github_explorer/__main__.py#main]",
                  "Repository maintenance scripts write their named documentation outputs or validate them; they do not execute gh. [src: scripts/generate_repo_indexes.py; scripts/check_doc_indexes.py]",
                  "generate_repo_indexes.py writes docs/high_signal_file_index.json, docs/codebase-overview.md and the docs/llms/ family. Existing owned output requires --refresh; foreign output is refused. [src: scripts/generate_repo_indexes.py#write]",
                  "check_doc_indexes.py reads the recorded manifest and compares source census and generated contents; it prints diagnostics and exits 1 on drift, or 0 on success. [src: scripts/check_doc_indexes.py#main]",
                  "", "## Quick answers",
                  "run → `github-explorer`, `ghx`, `python -m github_explorer` (Entrypoints). [src: pyproject.toml; src/github_explorer/__main__.py]",
                  "test → `uv run pytest` (CI commands). [src: .github/workflows/test.yml]",
                  "lint → `uv run ruff check .` (CI commands). [src: .github/workflows/test.yml]",
                  "build → `uv build` (CI commands). [src: .github/workflows/test.yml]"]
    architecture = ["## Architecture", *facts, "", "## Operations", *commands,
                    "", "## Conventions and gotchas",
                    "Use uv sync --locked, uv run pytest, uv run ruff check . and uv build for the documented development workflow. [src: README.md#development]",
                    "Opening the panel reads GitHub repository metadata and default-branch files; selecting a file reads its blob. Settings options come from local gh repo edit help and require confirmed changes. [src: src/github_explorer/panel.py; src/github_explorer/runner.py]",
                    "Catalog discovery reads local gh help; discovered aliases and extensions can execute external programs when explicitly requested. [src: src/github_explorer/catalog.py]",
                    "Stop cannot undo completed local or remote actions. [src: README.md#execution-behavior]",
                    "Shell expansion, pipelines and redirects are not supported by command execution. [src: README.md#execution-behavior]",
                    "## Development and maintenance",
                    "Restart the app after source changes; no service, database or watch server is required. Select the uv .venv interpreter for the integrated-terminal VS Code launch. [src: docs/DEVELOPMENT.md#prerequisites-and-setup]",
                    "Preserve the discovery/catalog.py, execution/runner.py, reusable UI/panel.py and standalone app.py seams. [src: docs/DEVELOPMENT.md#making-a-change]",
                    "A release change updates pyproject.toml, __init__.py, CHANGELOG.md and the project version in uv.lock together. [src: docs/DEVELOPMENT.md#making-a-change]",
                    "Run `uv run python scripts/generate_ops_registry_doc.py --check` and `uv run python scripts/check_doc_indexes.py` to detect generated-document drift. [src: docs/DEVELOPMENT.md#checks]",
                    "Use tmp_path, monkeypatch, fixture Python children and App.run_test(); verify observable effects and absence of execution before confirmation. [src: docs/TESTING.md#writing-tests]",
                    "No numeric coverage threshold or standalone type-checker is configured. Fixtures do not prove all gh versions, aliases, terminals or Enterprise deployments. [src: docs/TESTING.md#targets-and-ci-gates; docs/TESTING.md#limitations-and-smoke-checks]",
                    "## Runtime boundaries",
                    "The application has no listening port or persistent datastore. Operations metadata is not a second executor. [src: docs/ARCHITECTURE.md#context-and-containers; docs/ARCHITECTURE.md#components]",
                    "Local help calls each time out after 30 seconds. Captured mode defaults to 300 seconds; the UI accepts greater than zero through 86400 seconds. Terminal mode has no application timeout. [src: docs/ARCHITECTURE.md#deployment-and-quality-attributes]",
                    "Confirmation is a UX boundary, not a sandbox: installed gh/git, aliases, extensions and hooks retain the user's permissions and may run other programs. [src: docs/SECURITY.md#principals-and-trust-boundaries; docs/SECURITY.md#stride-review]",
                    "There is no durable command audit trail, central error file or remote telemetry. Sanitize captured text and arguments before copying or reporting them. [src: docs/SECURITY.md#secrets-input-and-output; docs/SECURITY.md#reporting-and-incidents]",
                    "The package exposes and consumes no MCP tools; project MCP configuration contains empty server maps. [src: docs/MCP.md]",
                    "--help and --version require no gh installation; --list-commands needs local gh help only. The ghx and github-explorer launchers are equivalent. [src: docs/INSTALLATION.md]",
                    "Catalog reload replaces the in-memory catalog; captured output retains at most two million characters and the visible log at most 5000 lines. No disk cache exists. [src: docs/caching-and-optimization.md]",
                    "Workflow rotation defaults to dry-run, a 200000-byte threshold and three retained sections; --apply writes archives and editor markers cause refusal. [src: docs/runbooks/metadata-maintenance.md]",
                    "The operation registry is declarative metadata and has no run/history/reset operation CLI. [src: docs/cli-and-operations.md]",
                    "The application has no direct HTTP SDK or configured API base URL; gh chooses endpoints. Repository indexes use static text and JSON with no Ollama process or watcher. [src: docs/integrations-and-assumptions.md]",
                    "## Documentation routing"]
    for path in paths:
        if path.startswith("docs/") and path.endswith(".md"):
            headings = re.findall(r"^#{1,2} (.+)$", sources[path], re.M)
            architecture.append(f"{path}: {'; '.join(headings)}. [src: {path}]")
    architecture.extend(["", "## Coverage limits",
                         "Source, scripts and tests have curated cards from direct review; remaining metadata cards are shallow. Parser definitions are statically extracted. [src: scripts/generate_repo_indexes.py]",
                         "Agent instructions and workflow logs are inventoried by path and hash only. No private instructions are copied into this dossier. [src: scripts/generate_repo_indexes.py]",
                         "Generated outputs are excluded from the source census to prevent recursive drift. No index, network, gh, or application probes were run for this dossier. [src: scripts/generate_repo_indexes.py]"])
    filemap = ["## File table of contents"]
    for card in cards:
        filemap.append(f"{card['path']} — {card['role']}, {card['importance']}, {card['bytes']} bytes; {card['depth']}. [src: {card['path']}]")
    filemap.append("\n## File cards")
    order = {"critical": 0, "high": 1, "normal": 2, "peripheral": 3}
    for card in sorted(cards, key=lambda c: (order[c["importance"]], c["path"])):
        filemap.extend([f"### {card['path']}",
                        f"Purpose: {card['purpose']} {card['provenance']}",
                        f"Read depth: {card['depth']}; role: {card['role']}; importance: {card['importance']}. [asserted]",
                        f"Link: {card['link']} [src: git]"])
        if card["depth"] == "deep-read":
            for key in ("why", "when", "how_to_read", "how_to_edit", "depends_on", "depended_on_by"):
                value = card[key]
                if isinstance(value, list):
                    value = ", ".join(value) or "None recorded"
                tag = card["edit_provenance"] if key == "how_to_edit" else card["provenance"]
                if key in {"why", "when"}:
                    tag = "[asserted]"
                filemap.append(f"{key}: {value} {tag}")
        else:
            filemap.append(f"Open when inspecting this {card['role']} file; semantic edit guidance and dependency edges are deferred. [asserted]")
        if card["symbols"]:
            filemap.append(f"Declared symbols: {', '.join(card['symbols'])}. [src: {card['path']}]")
    indexes = ["## Static indexes",
               "docs/high_signal_file_index.json and docs/llms/filemap.json store path, role, importance, size, hash, symbols and public source links. [src: scripts/generate_repo_indexes.py]",
               "docs/llms/manifest.json stores census, provenance and explicit scope limits. [src: scripts/generate_repo_indexes.py]",
               "Builder: `python scripts/generate_repo_indexes.py --refresh`; checker: `python scripts/check_doc_indexes.py`. [src: scripts/generate_repo_indexes.py; scripts/check_doc_indexes.py]",
               "Backend: plain JSON and text. Embedding model and dimensions: not applicable. Refresh is manual after source changes. [src: scripts/generate_repo_indexes.py]",
               "Query by reading JSON or searching docs/llms/; no semantic, keyword, or external index was built or probed. [src: scripts/generate_repo_indexes.py]"]
    links = []
    for path, source in sources.items():
        if path == "uv.lock":
            continue
        for url in sorted(set(re.findall(r'https://[^\s<>`"\)\]]+', source))):
            if not any(marker in url for marker in ("${", "{", "@")):
                links.append(f"{url} — unverified; no network reachability probe. [src: {path}]")
    infra = ["## Toolchain and CI", *facts[:4], *ci_commands, "", "## Environment", *env,
             "", "## Links", *links]
    manifest["executable_inventory"] = {
        "entrypoints": len(commands), "ci_commands": len(ci_commands),
        "explicit_parser_definitions": sum(len(info["options"]) for info in code.values()),
        "environment_names": sorted({
            name for path, source in sources.items() if path.startswith("src/")
            for name in re.findall(r"\b(?:GH_[A-Z_]+|PAGER|NO_COLOR)\b", source)
        }),
        "quick_answers": ["run", "test", "lint", "build"],
        "method": "AST parser calls and manifest/CI declarations; no target execution",
    }
    manifest["links"] = {"unverified": len(links), "verified": 0}
    history = ["## Recorded history (up to 200 commits)",
               "History records the generation snapshot; the checker retains that snapshot across commits. [src: scripts/generate_repo_indexes.py]",
               *(f"{line} [src: git]" for line in metadata["history"])]
    index = ["A static map of the public GitHub Explorer source tree. [src: pyproject.toml]", "",
             "## Read by task",
             "- [Architecture and operations](llms-full.txt#architecture)",
             "- [Conventions and limits](llms-full.txt#conventions-and-gotchas)",
             "- [Budget digest](llms-small.txt)", "- [Atomic facts](llms-facts.txt)",
             "- [Files and review cards](llms-filemap.txt)", "- [Index inventory](llms-indexes.txt)",
             "- [Infrastructure and links](llms-infra.txt)", "- [History](llms-history.txt)",
             "- [Executable and option inventory](llms-executable.txt)",
             "- [Machine-readable filemap](filemap.json)", "- [Provenance and exclusions](manifest.json)"]
    small = [*facts[:4], "", "## Key files"]
    small.extend(f"{c['path']} — {c['importance']}. [asserted]" for c in cards if c["importance"] in {"critical", "high"})
    small.extend(["", "## Run and verify", *commands[:3], *ci_commands, "",
                  "See llms-full.txt for limitations and llms-executable.txt for exact parser definitions. [src: scripts/generate_repo_indexes.py]"])
    overview = [*architecture, "", "## Complete source file map"]
    directories = sorted({str(Path(card["path"]).parent) for card in cards})
    for directory in directories:
        overview.append(f"### {directory}")
        for card in cards:
            if str(Path(card["path"]).parent) != directory:
                continue
            symbols = ", ".join(card["symbols"][:12])
            suffix = f" Key symbols: {symbols}." if symbols else ""
            overview.append(f"- {card['path']}: {card['purpose']}{suffix} {card['provenance']}")
    overview.extend(["", "## Generated outputs (excluded from recursive source census)"])
    overview.extend(f"- {path} [src: scripts/generate_repo_indexes.py]" for path in OUTPUTS)
    result = {
        "docs/high_signal_file_index.json": json_text({"schema_version": SCHEMA_VERSION, "files": cards}),
        "docs/codebase-overview.md": document("codebase overview", overview),
        "docs/llms/filemap.json": json_text(cards), "docs/llms/manifest.json": json_text(manifest),
    }
    for name, title, body in (
        ("llms", "routing index", index), ("llms-full", "static repository reference", architecture),
        ("llms-small", "budget digest", small), ("llms-facts", "atomic facts", facts),
        ("llms-filemap", "file inventory", filemap), ("llms-indexes", "index inventory", indexes),
        ("llms-infra", "infrastructure and links", infra), ("llms-history", "history", history),
        ("llms-executable", "executable inventory", executable),
    ):
        result[f"docs/llms/{name}.txt"] = document(title, body)
    for name, cap in (("llms.txt", 2000), ("llms-small.txt", 8000)):
        if len(result[f"docs/llms/{name}"].encode()) > cap:
            raise ValueError(f"{name} exceeds {cap}-byte cap")
    return result


def write(root: Path, *, refresh: bool = False) -> None:
    for output in OUTPUTS:
        destination = root / output
        for candidate in (destination, *destination.parents):
            if candidate == root:
                break
            if candidate.is_symlink():
                raise ValueError(f"Refusing symlinked generated path: {candidate.relative_to(root)}")
    target = root / "docs/llms"
    manifest_path = target / "manifest.json"
    if target.exists() and any(target.iterdir()):
        if not manifest_path.exists():
            raise ValueError("docs/llms is nonempty without a generator manifest")
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("generator") != GENERATOR:
            raise ValueError("docs/llms belongs to another generator")
        if manifest.get("remote") != snapshot(root)["remote"]:
            raise ValueError("docs/llms belongs to a different repository remote")
        if not refresh:
            raise ValueError("Existing dossier requires --refresh")
    for name, content in render(root).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Replace this generator's existing dossier")
    args = parser.parse_args()
    write(ROOT, refresh=args.refresh)
    print("Generated static repository indexes and dossier.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
