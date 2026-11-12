'use strict';
const { lstatSync, readdirSync } = require('node:fs');
const { join } = require('node:path');
const { version } = require('./package.json');
for (const directory of ['bin', 'python']) {
  if (!lstatSync(join(__dirname, directory)).isDirectory()) {
    throw new Error(`Package directory must be a real directory: ${directory}`);
  }
}
const files = [
  'bin/github-explorer.cjs',
  `python/github_explorer-${version}-py3-none-any.whl`, 'python/requirements.txt',
  'README.md', 'LICENSE', 'NOTICE.md',
];
for (const file of files) {
  if (!lstatSync(join(__dirname, file)).isFile()) {
    throw new Error(`Package entry must be a regular file: ${file}`);
  }
}
for (const directory of ['bin', 'python']) {
  for (const name of readdirSync(join(__dirname, directory))) {
    if (!files.includes(`${directory}/${name}`)) {
      throw new Error(`Unexpected package payload: ${directory}/${name}`);
    }
  }
}
