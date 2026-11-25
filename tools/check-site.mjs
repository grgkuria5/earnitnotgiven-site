import { readFile } from 'node:fs/promises';

const must = [
  ['dist/index.html', 'Earn It Not Given'],
  ['dist/index.html', 'Content-Security-Policy'],
  ['dist/index.html', 'strict-origin-when-cross-origin'],
  ['dist/index.html', 'Get 10% off your first order'],
  ['dist/tech-help/index.html', 'Ask for quote'],
  ['dist/ewaste-pickup/index.html', 'Join the pickup waitlist'],
  ['dist/ewaste-pickup/index.html', 'Join waitlist'],
  ['dist/ewaste-pickup/index.html', 'Pickups start soon'],
  ['dist/ewaste-pickup/index.html', "we don't buy electronics"],
  ['dist/ewaste-pickup/index.html', 'george@earnitnotgiven.com'],
  ['dist/ewaste-pickup/index.html', 'href="/privacy"'],
  ['dist/index.html', 'href="/ewaste-pickup"'],
  ['dist/about/index.html', 'Palo Alto'],
  ['dist/guardianorbit/index.html', 'Coming soon'],
  ['dist/guides/index.html', 'No guides are published yet'],
  ['dist/admin/index.html', 'sveltia-cms.js'],
  ['dist/admin/config.yml', 'repo: grgkuria5/earnitnotgiven-site'],
  ['dist/CNAME', 'www.earnitnotgiven.com'],
  ['dist/robots.txt', 'Disallow: /admin'],
  ['dist/.well-known/security.txt', 'sales@earnitnotgiven.com'],
  ['dist/designs/index.html', 'View on Etsy'],
  ['dist/shop/clothing/index.html', 'View on Etsy'],
  ['dist/shop/wall-art/index.html', 'View on Etsy'],
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
if (home.includes('Sample Flash') || home.includes('sample-14-inch-ultrabook')) {
  console.error('sample product leaked onto the home page');
  process.exit(1);
}
const sampleFile = await readFile('src/content/products/sample-14-inch-ultrabook.md', 'utf8');
if (!sampleFile.includes('sample: true')) {
  console.error('sample product file is missing from the content folder');
  process.exit(1);
}
const productTemplate = await readFile('src/pages/product/[slug].astro', 'utf8');
if (!productTemplate.includes('Also on Amazon')) {
  console.error('Also on Amazon is missing from the product template');
  process.exit(1);
}
if (home.includes('As an Amazon Associate')) {
  console.error('Amazon disclosure is showing while the tag is empty');
  process.exit(1);
}
const ewaste = await readFile('dist/ewaste-pickup/index.html', 'utf8');
if (ewaste.includes('notified the California Department of Toxic Substances Control')) {
  console.error('DTSC sentence is showing while e-waste launch mode is waitlist');
  process.exit(1);
}
if (/<(img|svg)\b[^>]*(R2|e-Stewards|NAID)/i.test(ewaste)) {
  console.error('certification badge found on the e-waste page');
  process.exit(1);
}
if (ewaste.includes('[[') || ewaste.includes('owner to confirm')) {
  console.error('unfilled e-waste placeholder is still on the page');
  process.exit(1);
}
console.log('site checks passed');
