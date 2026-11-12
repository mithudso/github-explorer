'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, mkdirSync, writeFileSync, copyFileSync, rmSync, symlinkSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, resolve } = require('node:path');
const { spawnSync } = require('node:child_process');

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'ghx-package-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const dir of ['bin', 'python']) mkdirSync(join(root, dir));
  copyFileSync(resolve(__dirname, '../check-package.cjs'), join(root, 'check-package.cjs'));
  writeFileSync(join(root, 'package.json'), JSON.stringify({ version: '0.0.1' }));
  for (const file of ['bin/github-explorer.cjs', 'python/github_explorer-0.0.1-py3-none-any.whl',
    'python/requirements.txt', 'README.md', 'LICENSE', 'NOTICE.md']) {
    writeFileSync(join(root, file), 'fixture');
  }
  return root;
}

function check(root) {
  return spawnSync(process.execPath, [join(root, 'check-package.cjs')], { encoding: 'utf8' });
}

test('accepts a complete regular-file package', t => {
  const result = check(fixture(t));
  assert.equal(result.status, 0, result.stderr);
});

for (const file of ['python/private.txt', 'bin/private.txt', 'python/nested']) {
  test(`rejects unexpected payload entry ${file}`, t => {
    const root = fixture(t);
    if (file.endsWith('nested')) mkdirSync(join(root, file));
    else writeFileSync(join(root, file), 'synthetic private marker');
    assert.notEqual(check(root).status, 0);
  });
}

for (const kind of ['directory', 'symlink', 'missing']) {
  test(`rejects a ${kind} wheel`, t => {
    const root = fixture(t);
    const wheel = join(root, 'python/github_explorer-0.0.1-py3-none-any.whl');
    rmSync(wheel);
    if (kind === 'directory') mkdirSync(wheel);
    if (kind === 'symlink') symlinkSync(join(root, 'LICENSE'), wheel);
    assert.notEqual(check(root).status, 0);
  });
}

test('requires the launcher', t => {
  const root = fixture(t);
  rmSync(join(root, 'bin/github-explorer.cjs'));
  assert.notEqual(check(root).status, 0);
});
