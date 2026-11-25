import { readFile } from 'node:fs/promises';

const must = [
  ['dist/index.html', 'Earn It Not Given'],
  ['dist/index.html', 'Content-Security-Policy'],
  ['dist/index.html', 'strict-origin-when-cross-origin'],
  ['dist/index.html', 'Get 10% off your first order'],
  ['dist/tech-help/index.html', 'Ask for quote'],
  ['dist/about/index.html', 'Palo Alto'],
  ['dist/guardianorbit/index.html', 'Coming soon'],
  ['dist/guides/index.html', 'No guides are published yet'],
  ['dist/admin/index.html', 'sveltia-cms.js'],
  ['dist/admin/config.yml', 'repo: grgkuria5/earnitnotgiven-site'],
  ['dist/CNAME', 'www.earnitnotgiven.com'],
  ['dist/robots.txt', 'Disallow: /admin'],
  ['dist/.well-known/security.txt', 'sales@earnitnotgiven.com'],
  ['dist/product/sample-14-inch-ultrabook/index.html', 'Also on Amazon'],
];

for (const [file, needle] of must) {
  const text = await readFile(file, 'utf8');
  if (!text.includes(needle)) {
    console.error(`missing ${JSON.stringify(needle)} in ${file}`);
    process.exit(1);
  }
}

const guides = await readFile('dist/guides/index.html', 'utf8');
if (guides.includes('Best budget laptops')) {
  console.error('draft guide leaked onto the public guides page');
  process.exit(1);
}
const home = await readFile('dist/index.html', 'utf8');
if (/onclick=|onsubmit=/i.test(home)) {
  console.error('inline event handler found');
  process.exit(1);
}
if (home.includes('As an Amazon Associate')) {
  console.error('Amazon disclosure is showing while the tag is empty');
  process.exit(1);
}
console.log('site checks passed');
