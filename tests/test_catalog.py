import subprocess

from github_explorer import catalog
from github_explorer.catalog import flags_from_help, parse_catalog

REFERENCE = """# gh reference

## gh pr <command>

Work with pull requests.

### gh pr create [flags]

Create a pull request.

  -t, --title string   Pull request title
      --draft          Create a draft

### gh pr list [flags]

List pull requests.

## gh repo <command>

Work with repositories.

### gh repo autolink <command>

Manage autolinks.

#### gh repo autolink delete <id> [flags]

Delete an autolink.
"""


def test_full_reference_and_extensions_are_parsed_without_execution():
    root = """CORE COMMANDS
  pr: Pull requests
ALIAS COMMANDS
  co: Alias for pr checkout
EXTENSION COMMANDS
  dash: Extension gh-dash
HELP TOPICS
  reference: All commands
"""
    commands = {c.name: c for c in parse_catalog(REFERENCE, root)}
    assert "repo autolink delete" in commands
    assert "reference" not in commands
    assert commands["co"].external and commands["dash"].external
    assert not commands["pr create"].external
    assert commands["pr create"].summary == "Create a pull request."
    flags = commands["pr create"].flags
    assert [(f.name, f.value_type) for f in flags] == [("--title", "string"), ("--draft", "")]


def test_flags_preserve_value_types_and_inherited_options():
    flags = flags_from_help("""
  -R, --repo [HOST/]OWNER/REPO   Select repository
      --json fields            JSON output
      --help                   Show help
""")
    assert [(f.name, f.value_type) for f in flags] == [
        ("--repo", "[HOST/]OWNER/REPO"),
        ("--json", "fields"),
        ("--help", ""),
    ]


def test_loading_uses_only_builtin_help_commands(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(catalog, "executable", lambda: "/mock/gh")

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        output = REFERENCE if argv[1:] == ["help", "reference"] else (
            "ALIAS COMMANDS\n  co: Alias for pr checkout\n"
            "EXTENSION COMMANDS\n  dash: Extension gh-dash\n"
        )
        return subprocess.CompletedProcess(argv, 0, output, "")

    monkeypatch.setattr(catalog.subprocess, "run", run)
    commands = catalog.load_catalog(tmp_path)
    assert [argv for argv, _ in calls] == [
        ["/mock/gh", "help", "reference"], ["/mock/gh", "--help"]
    ]
    assert {c.name for c in commands if c.external} == {"co", "dash"}
    for _, kwargs in calls:
        assert not kwargs.get("shell", False)
        assert kwargs["cwd"] == tmp_path
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["timeout"] == 30
