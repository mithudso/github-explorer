import base64
import json

import pytest

from github_explorer import catalog, runner


class FixtureRunner:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def run(self, invocation, on_output, timeout):
        self.calls.append(invocation)
        data = next(self.responses)
        return data if isinstance(data, runner.Result) else runner.Result(0, json.dumps(data))


def repository(tmp_path, branch="main"):
    return runner.Repository(
        runner.Invocation(("/fixture/gh", "repo", "view"), tmp_path),
        "owner/repo", "git.example.test", branch, {},
    )


def test_repository_identity_pins_host_and_cwd(tmp_path):
    context = runner.Invocation(("/fixture/gh", "repo", "view"), tmp_path, "git.example.test/o/r")
    executor = FixtureRunner([
        {"nameWithOwner": "o/r", "url": "https://git.example.test/o/r"},
        {"default_branch": "feature/main", "has_issues": False},
    ])
    info = runner.repository_info(context, executor)
    assert info.target == "git.example.test/o/r" and info.branch == "feature/main"
    assert executor.calls[0].repo == context.repo
    assert executor.calls[1].argv == (
        "/fixture/gh", "api", "--method", "GET", "--hostname", "git.example.test", "repos/o/r",
    )
    assert all(call.cwd == tmp_path for call in executor.calls)


def test_file_walk_lists_hidden_nested_files_and_submodules(tmp_path):
    executor = FixtureRunner([
        {"tree": [
            {"path": "src", "type": "tree", "sha": "tree1"},
            {"path": ".gitignore", "type": "blob", "sha": "blob1"},
            {"path": "lib", "type": "commit", "sha": "commit1"},
        ]},
        {"tree": [{"path": "a b.py", "type": "blob", "sha": "blob2"}]},
    ])
    files = runner.repository_files(repository(tmp_path, "feature/main"), executor)
    assert [file["path"] for file in files] == [".gitignore", "lib", "src/a b.py"]
    assert executor.calls[0].argv[-1].endswith("git/trees/feature%2Fmain")
    assert executor.calls[1].argv[-1].endswith("git/trees/tree1")
    assert all("GET" in call.argv and "recursive" not in call.argv[-1] for call in executor.calls)


def test_empty_and_truncated_trees(tmp_path):
    assert runner.repository_files(repository(tmp_path, ""), FixtureRunner([])) == []
    executor = FixtureRunner([runner.Result(1, "gh: Git Repository is empty. (HTTP 409)")])
    assert runner.repository_files(repository(tmp_path), executor) == []
    with pytest.raises(ValueError, match="incomplete"):
        runner.repository_files(repository(tmp_path), FixtureRunner([{"truncated": True}]))


@pytest.mark.parametrize("result, message", [
    (runner.Result(1, "permission denied"), "permission denied"),
    (runner.Result(0, "{}", cancelled=True), "cancelled"),
    (runner.Result(0, "{}", timed_out=True), "timed out"),
    (runner.Result(0, "{}", truncated=True), "capture limit"),
    (runner.Result(0, "[]"), "JSON object"),
    (runner.Result(0, "invalid json"), "Expecting value"),
])
def test_repository_read_errors_are_explicit(tmp_path, result, message):
    with pytest.raises(ValueError, match=message):
        runner.read_json(repository(tmp_path).context, FixtureRunner([result]))


def test_blob_previews_are_read_only_and_bounded(tmp_path):
    repo = repository(tmp_path)
    executor = FixtureRunner([
        {"encoding": "base64", "content": base64.b64encode(b"hello [bold]\n").decode()},
        {"encoding": "base64", "content": base64.b64encode(b"binary\0data").decode()},
    ])
    file = {"type": "blob", "sha": "blob1", "size": 15}
    assert runner.repository_file_text(repo, file, executor) == "hello [bold]\n"
    assert "Binary" in runner.repository_file_text(repo, file, executor)
    assert "500 KB" in runner.repository_file_text(repo, {**file, "size": 500_001}, executor)
    assert len(executor.calls) == 2
    assert "Submodule" in runner.repository_file_text(repo, {"type": "commit", "sha": "abc"}, executor)


def test_settings_discovery_includes_new_flags_without_executing_them(tmp_path, monkeypatch):
    calls = []
    def help_text(args, cwd):
        calls.append(args)
        return "  --future-setting string   Future option\n  --enable-issues   Enable issues\n  --help   Help\n"
    monkeypatch.setattr(catalog, "help_text", help_text)
    flags = catalog.repository_settings(tmp_path)
    assert [flag.name for flag in flags] == ["--future-setting", "--enable-issues"]
    assert calls == [["repo", "edit", "--help"]]
    assert catalog.setting_value(flags[0], {}) is None
    assert catalog.setting_value(flags[1], {}) is None
    assert catalog.setting_value(flags[1], {"has_issues": False}) is False


def test_settings_arguments_preserve_clear_and_false_require_visibility_acceptance():
    flags = (
        catalog.Flag("--description", "string"), catalog.Flag("--enable-issues"),
        catalog.Flag("--visibility", "string"), catalog.Flag("--accept-visibility-change-consequences"),
    )
    assert catalog.settings_arguments(flags, {"--description": "", "--enable-issues": "false"}) == [
        "--description=", "--enable-issues=false",
    ]
    for changes in [{}, {"--unknown": "x"}, {"--visibility": "private"}, {"--enable-issues": ""}]:
        with pytest.raises(ValueError):
            catalog.settings_arguments(flags, changes)
    args = catalog.settings_arguments(flags, {
        "--visibility": "private", "--accept-visibility-change-consequences": "true",
    })
    assert args == ["--visibility=private", "--accept-visibility-change-consequences=true"]


def test_squash_settings_current_mode_and_required_flag():
    flag = catalog.Flag("--squash-merge-commit-message", "string")
    assert catalog.setting_value(flag, {
        "squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "PR_BODY",
    }) == "pr-title-description"
    flags = (flag, catalog.Flag("--enable-squash-merge"))
    with pytest.raises(ValueError, match="enable-squash-merge"):
        catalog.settings_arguments(flags, {flag.name: "pr-title"})
    assert catalog.settings_arguments(flags, {
        flag.name: "pr-title", "--enable-squash-merge": "true",
    }) == ["--squash-merge-commit-message=pr-title", "--enable-squash-merge=true"]
