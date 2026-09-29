import json
import sys

import pytest

from github_explorer import runner


def invocation(tmp_path, code):
    return runner.Invocation((sys.executable, "-c", code), tmp_path, "example/project")


def test_exact_argv_context_and_no_shell(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "executable", lambda: "/usr/local/bin/gh")
    command = runner.prepare(
        'gh pr create --title "literal $(whoami)"', tmp_path, "example/project"
    )
    assert command.argv[-1] == "literal $(whoami)"
    assert command.cwd == tmp_path.resolve()
    assert command.environment()["GH_REPO"] == "example/project"
    assert command.environment()["GH_PROMPT_DISABLED"] == "1"
    for text in ["", "gh", "gh repo view && echo bad", "gh repo view | cat"]:
        with pytest.raises(ValueError):
            runner.prepare(text, tmp_path)
    with pytest.raises(ValueError, match="Repository"):
        runner.prepare("gh repo view", tmp_path, "https://example.com/o/r")
    monkeypatch.setenv("GH_REPO", "wrong/project")
    assert "GH_REPO" not in runner.prepare("gh repo view", tmp_path).environment()


def test_capture_exit_and_context(tmp_path):
    call = invocation(
        tmp_path,
        "import os,json; print(json.dumps([os.getcwd(),os.environ['GH_REPO']])); raise SystemExit(7)",
    )
    chunks = []
    result = runner.CommandRunner().run(call, chunks.append)
    assert result.returncode == 7
    assert json.loads(result.output) == [str(tmp_path), "example/project"]
    assert "".join(chunks) == result.output


def test_cancel_timeout_and_output_limit(tmp_path, monkeypatch):
    call = invocation(tmp_path, "import time; print('started',flush=True); time.sleep(30)")
    worker = runner.CommandRunner()
    result = worker.run(call, lambda text: worker.cancel())
    assert result.cancelled and result.returncode != 0
    result = runner.CommandRunner().run(call, lambda text: None, timeout=0.1)
    assert result.timed_out
    monkeypatch.setattr(runner, "OUTPUT_LIMIT", 100)
    result = runner.CommandRunner().run(invocation(tmp_path, "print('a'*1000)"), lambda text: None)
    assert len(result.output) == 100 and result.truncated
    assert result.returncode == 0


def test_cancel_before_start(tmp_path):
    worker = runner.CommandRunner()
    worker.cancel()
    target = tmp_path / "never-created"
    code = f"from pathlib import Path; Path({str(target)!r}).touch()"
    assert worker.run(invocation(tmp_path, code), lambda text: None).cancelled
    assert not target.exists()


def test_interactive_uses_normal_terminal(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        runner.subprocess, "call", lambda *args, **kwargs: calls.append((args, kwargs)) or 3
    )
    command = invocation(tmp_path, "pass")
    assert runner.run_interactive(command) == 3
    assert "stdin" not in calls[0][1] and "stdout" not in calls[0][1]
    assert calls[0][1]["cwd"] == tmp_path


def test_incomplete_utf8_is_replaced_at_eof(tmp_path):
    chunks = []
    result = runner.CommandRunner().run(
        invocation(tmp_path, "import os; os.write(1, b'prefix\\xe2\\x82')"), chunks.append
    )
    assert result.output == "prefix\ufffd"
    assert "".join(chunks) == result.output


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), -1, 0])
def test_invalid_timeout_cannot_start_a_process(tmp_path, monkeypatch, timeout):
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **kw: pytest.fail("started"))
    with pytest.raises(ValueError, match="Timeout"):
        runner.CommandRunner().run(invocation(tmp_path, "pass"), lambda text: None, timeout)


def test_git_context_env_and_literal_arguments(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "git_executable", lambda: "/fixture/git")
    monkeypatch.setenv("GH_REPO", "inherited/repo")
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)
    command = runner.prepare('git commit -m "literal $(whoami)"', tmp_path, "not a GitHub repo")
    assert command.argv == ("/fixture/git", "commit", "-m", "literal $(whoami)")
    assert command.program == "git" and command.repo == ""
    assert command.cwd == tmp_path.resolve()
    assert "override does not apply" in command.preview
    assert "GH_REPO" not in command.environment()
    assert "GH_REPO" not in command.environment(interactive=True)
    assert command.environment()["GIT_TERMINAL_PROMPT"] == "0"
    assert "GIT_TERMINAL_PROMPT" not in command.environment(interactive=True)
    for text in ["git", "git pull && git push", "git diff > patch"]:
        with pytest.raises(ValueError):
            runner.prepare(text, tmp_path)
    with pytest.raises(ValueError, match="directory"):
        runner.prepare("git status", tmp_path / "missing")


def test_missing_git_is_actionable(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    with pytest.raises(ValueError, match="Git is not installed"):
        runner.prepare("git status", tmp_path)
