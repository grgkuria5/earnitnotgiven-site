import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';

const dist = path.resolve('dist');
const files = [];

async function walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) await walk(full);
    else if (entry.name.endsWith('.html')) files.push(full);
  }
}

function localTarget(url) {
  const clean = url.split('#')[0].split('?')[0];
  if (!clean || clean.startsWith('mailto:') || clean.startsWith('tel:') || clean.startsWith('http:') || clean.startsWith('https:') || clean.startsWith('data:')) {
    return null;
  }
  if (!clean.startsWith('/')) return null;
  const rel = decodeURIComponent(clean.replace(/^\//, ''));
  return rel;
}

async function exists(rel) {
  const candidates = [
    path.join(dist, rel),
    path.join(dist, rel, 'index.html'),
    path.join(dist, `${rel}.html`),
  ];
  for (const candidate of candidates) {
    try {
      const info = await stat(candidate);
      if (info.isFile() || info.isDirectory()) return true;
    } catch {
      /* try next */
    }
  }
  return false;
}

await walk(dist);
const missing = [];
const linkRe = /(?:href|src)="([^"]+)"/g;
for (const file of files) {
  const html = await readFile(file, 'utf8');
  for (const match of html.matchAll(linkRe)) {
    const rel = localTarget(match[1]);
    if (rel === null) continue;
    if (!(await exists(rel))) missing.push(`${path.relative(dist, file)} -> ${match[1]}`);
  }
}
if (missing.length) {
  console.error(missing.join('\n'));
  process.exit(1);
}
console.log(`checked ${files.length} html files`);
