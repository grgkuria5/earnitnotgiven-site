import assert from 'node:assert/strict';
import test from 'node:test';
import {
  answerChat,
  buildCsp,
  escapeHtml,
  looksSensitive,
  paypalLines,
  publicHttpsUrl,
  renderRichText,
  stripeLink,
} from './pure.ts';

test('escapes markup', () => {
  assert.equal(escapeHtml('<script>"x"'), '&lt;script&gt;&quot;x&quot;');
});

test('markdown does not keep raw html', () => {
  const html = renderRichText('Hello <script>alert(1)</script>\n\n[[product:missing]]', { products: [], amazonTag: '' });
  assert.equal(html.includes('<script>'), false);
  assert.match(html, /not on the site/);
});

test('affiliate card has no price field', () => {
  const html = renderRichText('[[affiliate:amazon|Sleeve|https://www.amazon.com/dp/REPLACE|Placeholder]]', {
    products: [],
    amazonTag: '',
  });
  assert.match(html, /sponsored nofollow noopener noreferrer/);
  assert.equal(/\$\d/.test(html), false);
});

test('promo cents add up', () => {
  const quote = paypalLines(
    [
      { name: 'A', unitPrice: 10, qty: 2, sku: 'a' },
      { name: 'B', unitPrice: 5, qty: 1, sku: 'b' },
    ],
    'WELCOME10',
    [{ code: 'WELCOME10', label: '10%', percent: 10, active: true }],
  );
  const cents = quote.lines.reduce((sum, line) => sum + Math.round(Number(line.amount) * 100) * line.quantity, 0);
  assert.equal(cents, Math.round(quote.total * 100));
  assert.equal(quote.applied, 'WELCOME10');
});

test('csp allows paypal and a configured form host only', () => {
  const csp = buildCsp({ formOrigins: ['https://formspree.io'], connectOrigins: [], imgHosts: [] });
  assert.match(csp, /https:\/\/www\.paypal\.com/);
  assert.match(csp, /https:\/\/formspree\.io/);
  assert.equal(csp.includes('unsafe-inline'), false);
});

test('chat refuses card-like text and answers shipping', () => {
  const sensitive = answerChat('my card is 4242 4242 4242 4242', [], []);
  assert.match(sensitive.text, /do not send card numbers/i);
  const shipping = answerChat('how does shipping work?', [
    { id: 'shipping', question: 'How does shipping work?', keywords: ['ship', 'shipping'], answer: 'We ship from Palo Alto.' },
  ], []);
  assert.match(shipping.text, /Palo Alto/);
});

test('rejects localhost chat endpoints and loose stripe hosts', () => {
  assert.equal(publicHttpsUrl('http://127.0.0.1:11434'), '');
  assert.equal(publicHttpsUrl('https://localhost/chat'), '');
  assert.equal(stripeLink('https://example.com/pay'), '');
  assert.match(stripeLink('https://buy.stripe.com/test_123'), /buy\.stripe\.com/);
});

test('sensitive password phrase', () => {
  assert.equal(looksSensitive('my password is hunter2'), true);
});
