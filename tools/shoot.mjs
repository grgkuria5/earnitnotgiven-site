import puppeteer from 'puppeteer-core';
import { mkdir } from 'node:fs/promises';

const base = 'http://127.0.0.1:43123';
const out = '/opt/cursor/artifacts';
await mkdir(out, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: '/usr/bin/google-chrome',
  headless: true,
  args: ['--no-sandbox', '--disable-gpu'],
});
const problems = [];

async function shoot(name, path, width, height, fn) {
  const page = await browser.newPage();
  const logs = [];
  page.on('pageerror', (err) => logs.push(String(err)));
  page.on('console', (msg) => {
    if (msg.type() === 'error') logs.push(msg.text());
  });
  await page.setCacheEnabled(false);
  await page.setViewport({ width, height });
  const response = await page.goto(base + path, { waitUntil: 'networkidle0' });
  const status = response ? response.status() : 0;
  if (![200, 304].includes(status)) problems.push(`${path} status ${status}`);
  if (fn) await fn(page);
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: true });
  if (logs.length) problems.push(`${name}: ${logs.join(' | ')}`);
  await page.close();
}

await shoot('home-desktop', '/', 1440, 1100);
await shoot('home-mobile', '/', 390, 844);
await shoot('category-electronics', '/shop/electronics', 1440, 1000);
await shoot('product-amazon', '/product/sample-14-inch-ultrabook', 1280, 1100);
await shoot('about', '/about', 1280, 1000);
await shoot('guardianorbit', '/guardianorbit', 1280, 1000);
await shoot('guides', '/guides', 1280, 900);
await shoot('tech-help', '/tech-help', 1280, 1100);
await shoot('admin', '/admin/', 1280, 900, async (page) => {
  await new Promise((r) => setTimeout(r, 1500));
});
await shoot('newsletter', '/', 1280, 900, async (page) => {
  await page.evaluate(() => document.querySelector('#newsletter')?.scrollIntoView());
  await new Promise((r) => setTimeout(r, 300));
});
await shoot('chat-open', '/', 1280, 900, async (page) => {
  await page.click('[data-chat-open]');
  await new Promise((r) => setTimeout(r, 1800));
  await page.type('#chat-text', 'How does shipping work?');
  await page.click('[data-chat-send]');
  await page.waitForFunction(() => document.querySelectorAll('.bubble').length >= 3, { timeout: 5000 });
});

const cart = await browser.newPage();
await cart.setViewport({ width: 1280, height: 900 });
await cart.goto(base + '/cart', { waitUntil: 'networkidle0' });
await cart.evaluate(() => {
  localStorage.setItem('eing-cart-v1', JSON.stringify([{
    slug: 'demo', title: 'Demo checked item', unitPrice: 20, qty: 2, maxQty: 3, image: '', sample: false, digital: false, sku: 'DEMO'
  }]));
});
await cart.reload({ waitUntil: 'networkidle0' });
const total = await cart.$eval('#cart-root', (node) => node.textContent || '');
if (!total.includes('40.00') && !total.includes('36.00')) problems.push('cart total missing: ' + total.slice(0, 240));
await cart.screenshot({ path: `${out}/cart.png`, fullPage: true });
await cart.close();

const search = await browser.newPage();
await search.setViewport({ width: 1280, height: 800 });
await search.goto(base + '/search?q=ultrabook', { waitUntil: 'networkidle0' });
const shown = await search.$eval('[data-count]', (node) => node.textContent || '');
const hidden = await search.$$eval('[data-item]', (nodes) => nodes.filter((node) => node.hasAttribute('hidden')).length);
const visible = await search.$$eval('[data-item]', (nodes) => nodes.filter((node) => !node.hasAttribute('hidden')).length);
if (visible < 1) problems.push('search showed nothing for ultrabook');
await search.screenshot({ path: `${out}/search.png`, fullPage: true });
await search.close();

await browser.close();
console.log(JSON.stringify({ problems, shown, hidden, visible }, null, 2));
if (problems.length) process.exit(1);
