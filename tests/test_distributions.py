"""Keep release staging bounded to owned files and local output paths."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def builder(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / 'scripts/build_distributions.py'
    spec = importlib.util.spec_from_file_location('build_distributions', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    (tmp_path / 'npm').mkdir()
    (tmp_path / 'pyproject.toml').write_text('[project]\nversion = "1.2.3"\n')
    (tmp_path / 'npm/package.json').write_text(json.dumps({'version': '1.2.3'}))
    (tmp_path / 'packaging/homebrew').mkdir(parents=True)
    for name in ['README.md', 'LICENSE', 'NOTICE.md']:
        (tmp_path / name).write_text(f'Public {name}\n')
    calls = []
    monkeypatch.setattr(module.subprocess, 'run', lambda *args, **kwargs: calls.append(args))
    return module, calls


@pytest.mark.parametrize('name', ['private.txt', 'private-directory'])
def test_builder_refuses_unexpected_payload_before_any_build(builder, name):
    module, calls = builder
    payload = module.ROOT / 'npm/python'
    payload.mkdir()
    unknown = payload / name
    if 'directory' in name:
        unknown.mkdir()
    else:
        unknown.write_text('Keep local material')
    with pytest.raises(ValueError, match='Unexpected'):
        module.main()
    assert calls == [] and unknown.exists()
    assert not (module.ROOT / 'dist').exists()


@pytest.mark.parametrize('name', [
    'dist', 'npm/python', 'npm/python/requirements.txt',
    'npm/README.md', 'npm/LICENSE', 'npm/NOTICE.md',
    'packaging/homebrew/github-explorer.rb',
])
def test_builder_refuses_symlinks_before_any_mutation(builder, tmp_path_factory, name):
    module, calls = builder
    external = tmp_path_factory.mktemp('external-release')
    sentinel = external / 'keep.whl'
    sentinel.write_text('External sentinel')
    output = module.ROOT / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.symlink_to(external if name in {'dist', 'npm/python'} else sentinel)
    with pytest.raises(ValueError, match='symlink'):
        module.main()
    assert calls == [] and sentinel.read_text() == 'External sentinel'


def test_builder_stages_only_matching_release_and_removes_owned_old_wheel(builder, monkeypatch):
    module, _ = builder
    root = module.ROOT
    payload = root / 'npm/python'
    payload.mkdir()
    old = payload / 'github_explorer-1.0.0-py3-none-any.whl'
    old.write_text('old wheel')
    (root / 'uv.lock').write_text('package = []\n')

    def run(argv, **kwargs):
        if argv[1] == 'build':
            (root / 'dist').mkdir()
            (root / 'dist/github_explorer-1.2.3-py3-none-any.whl').write_bytes(b'new wheel')
            (root / 'dist/github_explorer-1.2.3.tar.gz').write_bytes(b'source archive')
        else:
            Path(argv[argv.index('--output-file') + 1]).write_text('')

    monkeypatch.setattr(module.subprocess, 'run', run)
    module.main()
    assert {path.name for path in payload.iterdir()} == {
        'github_explorer-1.2.3-py3-none-any.whl', 'requirements.txt',
    }
    assert (payload / 'github_explorer-1.2.3-py3-none-any.whl').read_bytes() == b'new wheel'
    assert (root / 'npm/NOTICE.md').read_text() == 'Public NOTICE.md\n'
    assert '/v1.2.3/github_explorer-1.2.3.tar.gz' in (root / 'packaging/homebrew/github-explorer.rb').read_text()


@pytest.mark.parametrize('name', [
    'README.md', 'LICENSE', 'NOTICE.md', 'pyproject.toml', 'uv.lock', 'MANIFEST.in',
    'npm/package.json', 'src', 'src/github_explorer/private.py', 'scripts', 'tests',
    'docs/operations-registry.json',
])
def test_builder_refuses_symlinked_release_inputs_before_build(builder, tmp_path_factory, name):
    module, calls = builder
    external = tmp_path_factory.mktemp('external-source')
    sentinel = external / 'private.txt'
    sentinel.write_text('Synthetic outside input to preserve')
    source = module.ROOT / name
    source.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        source.unlink()
    source.symlink_to(external if name in {'src', 'scripts', 'tests'} else sentinel)
    with pytest.raises(ValueError, match='symlink'):
        module.main()
    assert calls == []
    assert sentinel.read_text() == 'Synthetic outside input to preserve'
    assert not (module.ROOT / 'dist').exists()
    assert not (module.ROOT / 'npm/python').exists()
