'use strict';
const { existsSync } = require('node:fs');
const { join } = require('node:path');
const { version } = require('./package.json');
for (const file of [
  `python/github_explorer-${version}-py3-none-any.whl`, 'python/requirements.txt',
  'README.md', 'LICENSE', 'NOTICE.md',
]) {
  if (!existsSync(join(__dirname, file))) {
    throw new Error(`Missing ${file}. Run uv run python scripts/build_distributions.py first.`);
  }
}
