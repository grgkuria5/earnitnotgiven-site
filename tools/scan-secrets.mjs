import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const skip = new Set(['node_modules', 'dist', '.git', 'review']);
const patterns = [
  { name: 'private key', re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/ },
  { name: 'aws access key', re: /AKIA[0-9A-Z]{16}/ },
  { name: 'stripe secret', re: /sk_(live|test)_[0-9a-zA-Z]+/ },
  { name: 'github token', re: /ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}/ },
  { name: 'slack token', re: /xox[baprs]-[A-Za-z0-9-]{10,}/ },
];

const hits = [];
async function walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (skip.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      await walk(full);
      continue;
    }
    if (entry.name === 'sveltia-cms.js' || entry.name.endsWith('.png') || entry.name.endsWith('.woff') || entry.name.endsWith('.woff2')) continue;
    let text = '';
    try {
      text = await readFile(full, 'utf8');
    } catch {
      continue;
    }
    if (text.includes('\u0000')) continue;
    for (const pattern of patterns) {
      if (pattern.re.test(text)) hits.push(`${path.relative('.', full)}: ${pattern.name}`);
    }
  }
}

await walk(path.resolve('.'));
if (hits.length) {
  console.error(hits.join('\n'));
  console.error('Do not commit secrets. See the Security section of the README.');
  process.exit(1);
}
console.log('secret scan clean');
