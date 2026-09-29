#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const { existsSync } = require('node:fs');
const { join } = require('node:path');
const { version } = require('../package.json');

const wheel = join(__dirname, '..', 'python', `github_explorer-${version}-py3-none-any.whl`);
const requirements = join(__dirname, '..', 'python', 'requirements.txt');
if (!existsSync(wheel) || !existsSync(requirements)) {
  console.error('GitHub Explorer package is incomplete. Reinstall the npm package.');
  process.exit(1);
}

// Keep the caller's working directory and terminal. Never interpret arguments in a shell.
const result = spawnSync('uv', [
  'tool', 'run', '--no-config', '--isolated', '--python', '>=3.11',
  '--from', wheel, '--with-requirements', requirements, '--',
  'github-explorer', ...process.argv.slice(2),
], { stdio: 'inherit' });

if (result.error) {
  console.error(result.error.code === 'ENOENT'
    ? 'GitHub Explorer requires uv on PATH. Install it: https://docs.astral.sh/uv/getting-started/installation/'
    : `Unable to start GitHub Explorer: ${result.error.message}`);
  process.exit(1);
}
if (result.signal) process.kill(process.pid, result.signal);
else process.exit(result.status ?? 1);
