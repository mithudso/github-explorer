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
