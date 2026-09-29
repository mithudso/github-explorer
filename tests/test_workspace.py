import json
import subprocess

import pytest

from github_explorer import runner


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def checkout(tmp_path):
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Fixture')
    git(tmp_path, 'config', 'user.email', 'fixture@example.invalid')
    (tmp_path / 'a.txt').write_text('original\n')
    (tmp_path / 'b.txt').write_text('other\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-m', 'fixture')
    return tmp_path


def test_real_git_counts_unique_changes_and_current_branch(checkout):
    (checkout / 'a.txt').write_text('staged\n')
    git(checkout, 'add', 'a.txt')
    (checkout / 'a.txt').write_text('unstaged too\n')
    git(checkout, 'mv', 'b.txt', 'renamed with\nnewline.txt')
    (checkout / 'new.txt').write_text('new\n')
    git(checkout, 'branch', 'feature')
    state = runner.workspace_status(checkout, runner.CommandRunner())
    assert state.branch == 'main' and state.changed == 3
    assert set(state.branches) == {'main', 'feature'}
    files = runner.workspace_files(state, runner.CommandRunner())
    assert {entry['path'] for entry in files} == {'a.txt', 'renamed with\nnewline.txt', 'new.txt'}
    git(checkout, 'checkout', '--detach')
    assert runner.workspace_status(checkout, runner.CommandRunner()).branch.startswith('detached@')


def test_unborn_branch_and_deleted_files(tmp_path):
    git(tmp_path, 'init', '-b', 'brand-new')
    state = runner.workspace_status(tmp_path, runner.CommandRunner())
    assert state.branch == 'brand-new' and state.changed == 0
    assert runner.changed_file_count(' D removed\0UU conflict\0?? untracked\0') == 3


def test_editable_file_boundaries(checkout, tmp_path):
    state = runner.workspace_status(checkout, runner.CommandRunner())
    assert runner.editable_file(state, 'a.txt') == checkout / 'a.txt'
    for name in ['../outside', '/etc/passwd', '.git/config', 'missing', '.']:
        with pytest.raises(ValueError):
            runner.editable_file(state, name)
    (checkout / 'link').symlink_to(checkout / 'a.txt')
    with pytest.raises(ValueError, match='Symlink'):
        runner.editable_file(state, 'link')
    (checkout / 'binary').write_bytes(b'a\0b')
    with pytest.raises(ValueError, match='Binary'):
        runner.editable_file(state, 'binary')
    (checkout / 'latin').write_bytes(b'\xff')
    with pytest.raises(ValueError, match='UTF-8'):
        runner.editable_file(state, 'latin')
    (checkout / 'large').write_bytes(b'x' * 500001)
    with pytest.raises(ValueError, match='500 KB'):
        runner.editable_file(state, 'large')


def test_vim_command_quotes_paths_disables_session_files(checkout, monkeypatch):
    monkeypatch.setattr(runner.shutil, 'which', lambda name: '/fixture/vim')
    state = runner.Workspace(checkout, 'main', 0, ())
    path = checkout / 'spaces | "quotes".txt'
    argv = runner.vim_command(state, path)
    assert argv[0] == '/fixture/vim' and argv[-2:] == ['--', str(path)]
    assert argv[argv.index('-i') + 1] == 'NONE' and '-n' in argv
    monkeypatch.setattr(runner.shutil, 'which', lambda name: None)
    with pytest.raises(ValueError, match='Vim is not installed'):
        runner.vim_command(state, path)


def test_repository_activity_is_paginated_read_only_and_contextual(tmp_path):
    class FixtureRunner:
        def __init__(self):
            self.calls = []
        def run(self, invocation, output, timeout):
            self.calls.append(invocation)
            data = [{'number': 9, 'title': 'Fixture', 'url': 'https://host/o/r/pull/9'}] if len(self.calls) == 1 else ['main', 'feature']
            # gh emits one projected JSON object per page, without --slurp.
            output = json.dumps({'items': data})
            if len(self.calls) == 1:
                output += '\n' + json.dumps({'items': [{'number': 10, 'title': 'Next page', 'url': 'https://host/o/r/pull/10'}]})
            return runner.Result(0, output)
    executor = FixtureRunner()
    context = runner.Invocation(('/fixture/gh',), tmp_path, 'host/o/r')
    repo = runner.Repository(context, 'o/r', 'host', 'main', {})
    prs, branches = runner.repository_activity(repo, executor)
    assert [pr['number'] for pr in prs] == [9, 10] and branches == ['main', 'feature']
    for call in executor.calls:
        assert '--paginate' in call.argv and '--slurp' not in call.argv
        assert '--jq' in call.argv
        assert call.argv[call.argv.index('--method') + 1] == 'GET'
        assert call.argv[call.argv.index('--hostname') + 1] == 'host'
        assert call.cwd == tmp_path and call.repo == 'host/o/r'


def test_checkout_matching_ignores_override_and_checks_host(tmp_path):
    class FixtureRunner:
        def run(self, invocation, output, timeout):
            assert invocation.repo == ''
            return runner.Result(0, json.dumps({'nameWithOwner':'owner/repo', 'url':'https://github.com/owner/repo'}))
    state = runner.Workspace(tmp_path, 'main', 0, ())
    context = runner.Invocation(('/fixture/gh',), tmp_path, 'other/repo')
    repo = runner.Repository(context, 'other/repo', 'github.com', 'main', {})
    assert not runner.workspace_matches(repo, state, FixtureRunner())
