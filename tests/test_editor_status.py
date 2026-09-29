import shutil

import pytest
from textual.widgets import Static, Tree

from github_explorer import catalog, runner
from github_explorer.app import GitHubExplorer
from github_explorer.panel import VimEditor

pytestmark = pytest.mark.usefixtures('ui_repository')


@pytest.fixture
def local_files(tmp_path, monkeypatch):
    (tmp_path / 'a.txt').write_text('original\n')
    (tmp_path / 'b.txt').write_text('other\n')
    monkeypatch.setattr(catalog, 'load_catalog', lambda path: [])
    monkeypatch.setattr(runner, 'workspace_status', lambda cwd, executor: runner.Workspace(tmp_path, 'feature', 2, ('main', 'feature')))
    monkeypatch.setattr(runner, 'workspace_matches', lambda *args: True)
    monkeypatch.setattr(runner, 'workspace_files', lambda *args: [{'path': name, 'type': 'local'} for name in ['a.txt', 'b.txt']])
    monkeypatch.setattr(runner, 'repository_activity', lambda *args: ([{'number': 7, 'title': 'Open PR', 'url': 'https://github.com/owner/repository/pull/7'}], ['main', 'feature', 'remote-only']))


async def settle(pilot, predicate, timeout=5):
    for _ in range(int(timeout / 0.05)):
        if predicate():
            return
        await pilot.pause(0.05)
    assert predicate()


async def test_status_remains_visible_when_actions_hidden(tmp_path, local_files):
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        summary = str(panel.query_one('#gh-repository-status', Static).render())
        assert 'Branch: feature' in summary and 'Changed: 2' in summary
        assert 'PRs: 1 (#7)' in summary and 'Other branches: 2' in summary
        await pilot.press('ctrl+b')
        assert not panel.query_one('#gh-buttons').display
        assert not panel.query_one('#gh-quick-buttons').display
        assert panel.query_one('#gh-persistent-status').display
        assert panel.query_one('#gh-persistent-status').region.bottom == 40
        await pilot.click('#gh-toggle-actions')
        assert panel.query_one('#gh-buttons').display
        assert panel.query_one('#gh-quick-buttons').display


@pytest.mark.skipif(not shutil.which('vim'), reason='Vim unavailable')
async def test_real_vim_saves_and_protects_unsaved_file_switch(tmp_path, local_files, monkeypatch):
    from bittty import Board
    starts = []
    original = Board.start_process
    async def start_once(board):
        await original(board)
        starts.append(board.process)
    monkeypatch.setattr(Board, 'start_process', start_once)
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        panel = app.screen
        tree = panel.query_one('#gh-files', Tree)
        tree.select_node(tree.root.children[0])
        await settle(pilot, lambda: panel.editor is not None and panel.editor.board.process is not None)
        await pilot.pause(0.3)
        editor = panel.editor
        assert len(starts) == 1 and starts[0].poll() is None
        assert isinstance(editor, VimEditor) and app.focused is editor
        assert not panel.query_one('#gh-command-controls').display
        await pilot.click('#gh-toggle-actions')
        await pilot.resize_terminal(100, 35)
        await pilot.click('#gh-toggle-actions')
        await pilot.resize_terminal(120, 40)
        editor.focus()
        await pilot.press('i', *'inserted ', 'escape')
        assert app.screen is panel and panel.editor is editor
        assert (tmp_path / 'a.txt').read_text() == 'original\n'
        await pilot.press('ctrl+s')
        await settle(pilot, lambda: (tmp_path / 'a.txt').read_text() == 'inserted original\n')
        await pilot.press('A', *' unsaved', 'escape', 'ctrl+backslash')
        assert app.focused is tree
        tree.select_node(tree.root.children[1])
        await pilot.pause(0.3)
        # Vim's confirm-edit dialog lets the user cancel switching without losing the buffer.
        await pilot.press('c')
        await pilot.pause(0.1)
        await pilot.press('escape', ':', 'w', 'enter')
        await settle(pilot, lambda: 'unsaved' in (tmp_path / 'a.txt').read_text())
        assert (tmp_path / 'b.txt').read_text() == 'other\n'
        await pilot.press('ctrl+q')
        assert panel.editor is editor
        await pilot.click('#gh-close')
        assert panel.editor is editor  # App close cannot kill an active Vim buffer.
        await pilot.press('escape', ':', 'q', 'enter')
        await settle(pilot, lambda: panel.editor is None)
        assert not list(tmp_path.glob('*.swp')) and not (tmp_path / '.viminfo').exists()
        assert panel.query_one('#gh-command-controls').display
        assert starts[0].poll() == 0


async def test_status_failures_are_unknown_and_stale_results_ignored(tmp_path, local_files):
    app = GitHubExplorer(tmp_path)
    async with app.run_test():
        await app.workers.wait_for_complete()
        panel = app.screen
        current = panel.repository
        panel.activity_loaded(current, None, None, 'access denied')
        text, details = panel.repository_status_text()
        assert 'PRs: unknown' in text and 'access denied' in details
        old = runner.Repository(current.context, 'old/repo', 'github.com', 'main', {})
        panel.activity_loaded(old, [], [], '')
        assert panel.open_prs is None
        panel.local_status_loaded(str(tmp_path / 'old'), None, 'old error')
        assert panel.local_status.branch == 'feature'


async def test_refresh_updates_changed_count_and_missing_vim_is_reported(tmp_path, local_files, monkeypatch):
    app = GitHubExplorer(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await app.workers.wait_for_complete()
        panel = app.screen
        monkeypatch.setattr(runner, 'workspace_status', lambda cwd, executor: runner.Workspace(tmp_path, 'feature', 5, ('main', 'feature')))
        panel.refresh_local_status()
        await app.workers.wait_for_complete()
        assert 'Changed: 5' in str(panel.query_one('#gh-repository-status', Static).render())
        def unavailable(*args):
            raise ValueError('Vim is not installed or is not on PATH')
        monkeypatch.setattr(runner, 'vim_command', unavailable)
        tree = panel.query_one('#gh-files', Tree)
        tree.select_node(tree.root.children[0])
        await pilot.pause()
        assert panel.editor is None
        assert 'Vim is not installed' in str(panel.query_one('#gh-status', Static).render())
        assert not panel.query_one('#gh-cwd').disabled


async def test_mismatched_checkout_remains_read_only(tmp_path, local_files, monkeypatch):
    from textual.widgets import TextArea
    monkeypatch.setattr(runner, 'workspace_matches', lambda *args: False)
    monkeypatch.setattr(runner, 'repository_files', lambda *args: [{'path': 'a.txt', 'type': 'blob', 'sha': 'fixture'}])
    monkeypatch.setattr(runner, 'repository_file_text', lambda *args: 'remote text')
    app = GitHubExplorer(tmp_path, repo='different/repository')
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        panel = app.screen
        tree = panel.query_one('#gh-files', Tree)
        tree.select_node(tree.root.children[0])
        await pilot.pause()
        await app.workers.wait_for_complete()
        assert panel.editor is None and panel.workspace is None
        assert panel.query_one('#gh-file-preview', TextArea).text == 'remote text'
        assert (tmp_path / 'a.txt').read_text() == 'original\n'
        await pilot.press('ctrl+s')
        assert (tmp_path / 'a.txt').read_text() == 'original\n'
