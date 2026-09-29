const { test } = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, mkdirSync, writeFileSync, copyFileSync, readFileSync, realpathSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const { spawnSync } = require('node:child_process');

function fixture(t) {
  const root = realpathSync(mkdtempSync(join(tmpdir(), 'ghx npm ')));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const dir of ['bin', 'python', 'tools', 'checkout']) mkdirSync(join(root, dir));
  copyFileSync(resolve(__dirname, '../bin/github-explorer.cjs'), join(root, 'bin/cli.cjs'));
  writeFileSync(join(root, 'package.json'), JSON.stringify({ version: '0.0.1' }));
  writeFileSync(join(root, 'python/github_explorer-0.0.1-py3-none-any.whl'), 'fixture');
  writeFileSync(join(root, 'python/requirements.txt'), '');
  return root;
}

test('preserves literal arguments, checkout cwd and child exit status', t => {
  const root = fixture(t);
  const capture = join(root, 'capture.json');
  writeFileSync(join(root, 'tools/uv'), `#!${process.execPath}\n` +
    `require('node:fs').writeFileSync(process.env.CAPTURE, JSON.stringify({args:process.argv.slice(2),cwd:process.cwd()}));process.exit(7);\n`, { mode: 0o755 });
  const args = ['--cwd', 'path with spaces', '--repo', 'owner/repo; $(touch nope)'];
  const child = spawnSync(process.execPath, [join(root, 'bin/cli.cjs'), ...args], {
    cwd: join(root, 'checkout'), encoding: 'utf8',
    env: { ...process.env, PATH: join(root, 'tools'), CAPTURE: capture },
  });
  assert.equal(child.status, 7, child.stderr);
  const result = JSON.parse(readFileSync(capture, 'utf8'));
  assert.deepEqual(result.args.slice(-args.length), args);
  assert.equal(result.cwd, realpathSync(join(root, 'checkout')));
  assert.ok(result.args.includes('--isolated'));
  assert.ok(result.args.includes('--no-config'));
  assert.ok(result.args.includes(join(root, 'python/github_explorer-0.0.1-py3-none-any.whl')));
  assert.ok(result.args.includes(join(root, 'python/requirements.txt')));
});

test('explains missing uv without installing software at npm install time', t => {
  const root = fixture(t);
  const child = spawnSync(process.execPath, [join(root, 'bin/cli.cjs')], {
    encoding: 'utf8', env: { ...process.env, PATH: join(root, 'tools') },
  });
  assert.equal(child.status, 1);
  assert.match(child.stderr, /requires uv on PATH/);
});

test('rejects incomplete npm packages', t => {
  const root = fixture(t);
  rmSync(join(root, 'python/requirements.txt'));
  const child = spawnSync(process.execPath, [join(root, 'bin/cli.cjs')], { encoding: 'utf8' });
  assert.equal(child.status, 1);
  assert.match(child.stderr, /package is incomplete/);
});
