/** Pure helpers shared by the static build and the browser. No secrets, no network. */

export type ThemeName = 'default' | 'holiday' | 'sale';

export type PromoCode = {
  code: string;
  label: string;
  percent: number;
  active: boolean;
};

export type Settings = {
  business_name: string;
  tagline: string;
  paypal_business_email: string;
  amazon_associates_tag: string;
  newegg_affiliate_id: string;
  bestbuy_affiliate_id: string;
  bh_affiliate_id: string;
  other_affiliate_id: string;
  app_store_url: string;
  active_theme: ThemeName;
  contact_email: string;
  sales_email: string;
  location_label: string;
  form_endpoint: string;
  newsletter_form_action: string;
  newsletter_email_field: string;
  welcome_promo_code: string;
  welcome_promo_percent: number;
  welcome_promo_message: string;
  chat_ai_endpoint: string;
  return_window_days: number;
  google_site_verification: string;
  analytics_provider: '' | 'cloudflare' | 'goatcounter';
  analytics_token: string;
  promo_codes: PromoCode[];
  color_shift: boolean;
  color_shift_seconds: number;
  shift_gold: string;
  shift_blue: string;
  shift_teal: string;
  refreshed_banner: boolean;
  refreshed_messages: string[];
  ebay_flat_shipping_usd: number;
  ewaste_launch_mode: 'waitlist' | 'live';
  ewaste_partner_name: string;
  ewaste_phone: string;
  ewaste_response_time: string;
  ewaste_year: string;
};

export type FaqItem = {
  id: string;
  question: string;
  keywords: string[];
  answer: string;
};

export type ChatLink = { href: string; label: string };

export type ChatReply = {
  text: string;
  links: ChatLink[];
  confident: boolean;
};

const THEMES: ThemeName[] = ['default', 'holiday', 'sale'];

export function hexColor(value: unknown, fallback: string): string {
  const raw = String(value ?? '').trim();
  return /^#[0-9a-fA-F]{6}$/.test(raw) ? raw : fallback;
}

export function shiftSeconds(value: unknown): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return 16;
  return Math.min(20, Math.max(12, Math.round(n)));
}

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export function money(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(round2(n));
}

export function effectivePrice(price: number, sale?: number | null): number {
  if (typeof sale === 'number' && sale > 0 && sale < price) return round2(sale);
  return round2(price);
}

/** Minutes east of UTC for America/Los_Angeles at a UTC instant. */
export function pacificOffsetMinutes(utcMs: number): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Los_Angeles',
    timeZoneName: 'shortOffset',
    hour: '2-digit',
  }).formatToParts(new Date(utcMs));
  const name = parts.find((part) => part.type === 'timeZoneName')?.value ?? 'GMT-8';
  const match = name.match(/GMT([+-])(\d{1,2})(?::(\d{2}))?/);
  if (!match) return -8 * 60;
  const sign = match[1] === '-' ? -1 : 1;
  return sign * (Number(match[2]) * 60 + Number(match[3] || 0));
}

/** Parse a datetime. A value with no zone is Pacific Time (America/Los_Angeles). */
export function parsePacific(value: string): number | null {
  const raw = value.trim();
  if (!raw) return null;
  if (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(raw)) {
    const parsed = Date.parse(raw);
    return Number.isNaN(parsed) ? null : parsed;
  }
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6] || 0);
  let utc = Date.UTC(year, month - 1, day, hour, minute, second);
  for (let pass = 0; pass < 2; pass += 1) {
    utc = Date.UTC(year, month - 1, day, hour, minute, second) - pacificOffsetMinutes(utc) * 60 * 1000;
  }
  return utc;
}

export type FlashPhase = 'none' | 'before' | 'live' | 'after';

export function flashPhase(now: number, start: number | null, end: number | null): FlashPhase {
  if (start === null || end === null || end <= start) return 'none';
  if (now < start) return 'before';
  if (now >= end) return 'after';
  return 'live';
}

export function flashPercent(price: number, flashPrice: number): number {
  if (!(price > 0) || !(flashPrice > 0) || flashPrice >= price) return 0;
  return Math.round((1 - flashPrice / price) * 100);
}

export function countdownLabel(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  const clock = [hours, minutes, seconds].map((part) => String(part).padStart(2, '0')).join(':');
  return days > 0 ? `${days}d ${clock}` : clock;
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/['’]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value.trim() : fallback;
}

function clampPercent(value: unknown, fallback: number): number {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(90, Math.max(0, Math.round(n)));
}

/** https URL whose host is public. Rejects localhost, link-local, and private ranges. */
export function publicHttpsUrl(value: string): string {
  const raw = value.trim();
  if (!raw) return '';
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return '';
  }
  if (url.protocol !== 'https:' || url.username || url.password) return '';
  const host = url.hostname.toLowerCase().replace(/^\[|\]$/g, '');
  if (
    host === 'localhost' ||
    host.endsWith('.localhost') ||
    host.endsWith('.local') ||
    host === '0.0.0.0' ||
    host === '::1'
  ) {
    return '';
  }
  if (
    /^(127\.|10\.|192\.168\.|169\.254\.|0\.|172\.(1[6-9]|2\d|3[0-1])\.)/.test(host) ||
    host.startsWith('fc') ||
    host.startsWith('fd') ||
    host.startsWith('fe80')
  ) {
    return '';
  }
  return url.toString();
}

export function safeUrl(value: string): string {
  const raw = value.trim();
  if (!raw) return '';
  if (raw.startsWith('/') && !raw.startsWith('//')) return raw;
  if (/^mailto:/i.test(raw)) {
    const addr = raw.slice(7).split('?')[0];
    if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(addr)) return raw;
    return '';
  }
  return publicHttpsUrl(raw);
}

export function isExternal(href: string): boolean {
  return /^https?:\/\//i.test(href);
}

export function externalRel(href: string, affiliate = false): string {
  if (!isExternal(href)) return '';
  return affiliate ? 'sponsored nofollow noopener noreferrer' : 'noopener noreferrer';
}

export function hostOf(value: string): string | null {
  const safe = publicHttpsUrl(value);
  if (!safe) return null;
  return new URL(safe).host;
}

const STRIPE_HOSTS = new Set(['buy.stripe.com', 'checkout.stripe.com', 'pay.stripe.com']);

export function stripeLink(value: string): string {
  const safe = publicHttpsUrl(value);
  if (!safe) return '';
  const host = new URL(safe).hostname.toLowerCase();
  return STRIPE_HOSTS.has(host) ? safe : '';
}

export function appleStoreLink(value: string): string {
  const safe = publicHttpsUrl(value);
  if (!safe) return '';
  return new URL(safe).hostname.toLowerCase() === 'apps.apple.com' ? safe : '';
}

export function amazonLink(value: string): string {
  const safe = publicHttpsUrl(value);
  if (!safe) return '';
  const host = new URL(safe).hostname.toLowerCase();
  if (host === 'amazon.com' || host.endsWith('.amazon.com') || host.endsWith('.amazon.co.uk') || host.endsWith('.amazon.ca') || host.endsWith('.amazon.de')) {
    return safe;
  }
  return '';
}

export function etsyLink(value: string): string {
  const safe = publicHttpsUrl(value);
  if (!safe) return '';
  const host = new URL(safe).hostname.toLowerCase();
  return host === 'etsy.com' || host.endsWith('.etsy.com') ? safe : '';
}

export function withAmazonTag(value: string, tag: string): string {
  const safe = amazonLink(value);
  if (!safe || !tag.trim()) return safe;
  const url = new URL(safe);
  if (!url.searchParams.has('tag')) url.searchParams.set('tag', tag.trim());
  return url.toString();
}

export function paypalReady(email: string): boolean {
  const e = email.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return false;
  if (e.includes('replace') || e.includes('example.com') || e.endsWith('.invalid') || e.startsWith('you@')) {
    return false;
  }
  return true;
}

export function normalizeSettings(input: unknown): Settings {
  const raw = asRecord(input);
  const theme = asString(raw.active_theme, 'default') as ThemeName;
  const promosRaw = Array.isArray(raw.promo_codes) ? raw.promo_codes : [];
  const promo_codes: PromoCode[] = promosRaw.map((item) => {
    const row = asRecord(item);
    return {
      code: asString(row.code).toUpperCase(),
      label: asString(row.label),
      percent: clampPercent(row.percent, 0),
      active: row.active !== false,
    };
  }).filter((row) => row.code);

  return {
    business_name: asString(raw.business_name, 'Earn It Not Given LLC'),
    tagline: asString(raw.tagline, 'Hand-tested tech from a small shop in Palo Alto.'),
    paypal_business_email: asString(raw.paypal_business_email),
    amazon_associates_tag: asString(raw.amazon_associates_tag).replace(/[^\w-]/g, ''),
    newegg_affiliate_id: asString(raw.newegg_affiliate_id),
    bestbuy_affiliate_id: asString(raw.bestbuy_affiliate_id),
    bh_affiliate_id: asString(raw.bh_affiliate_id),
    other_affiliate_id: asString(raw.other_affiliate_id),
    app_store_url: appleStoreLink(asString(raw.app_store_url)),
    active_theme: THEMES.includes(theme) ? theme : 'default',
    contact_email: asString(raw.contact_email, 'george@earnitnotgiven.com'),
    sales_email: asString(raw.sales_email, 'sales@earnitnotgiven.com'),
    location_label: asString(raw.location_label, 'Palo Alto, CA'),
    form_endpoint: publicHttpsUrl(asString(raw.form_endpoint)),
    newsletter_form_action: publicHttpsUrl(asString(raw.newsletter_form_action)),
    newsletter_email_field: asString(raw.newsletter_email_field, 'email').replace(/[^\w-]/g, '') || 'email',
    welcome_promo_code: asString(raw.welcome_promo_code, 'WELCOME10').toUpperCase(),
    welcome_promo_percent: clampPercent(raw.welcome_promo_percent, 10),
    welcome_promo_message: asString(raw.welcome_promo_message, 'Get 10% off your first order'),
    chat_ai_endpoint: publicHttpsUrl(asString(raw.chat_ai_endpoint)),
    return_window_days: (() => {
      const days = Number(raw.return_window_days);
      return Number.isFinite(days) ? Math.min(365, Math.max(0, Math.round(days))) : 30;
    })(),
    google_site_verification: asString(raw.google_site_verification).replace(/[^\w-]/g, ''),
    analytics_provider: (['cloudflare', 'goatcounter'].includes(asString(raw.analytics_provider))
      ? asString(raw.analytics_provider)
      : '') as '' | 'cloudflare' | 'goatcounter',
    analytics_token: asString(raw.analytics_token).replace(/[^a-zA-Z0-9._-]/g, ''),
    promo_codes,
    color_shift: raw.color_shift !== false,
    color_shift_seconds: shiftSeconds(raw.color_shift_seconds),
    shift_gold: hexColor(raw.shift_gold, '#e0b45a'),
    shift_blue: hexColor(raw.shift_blue, '#1c3f73'),
    shift_teal: hexColor(raw.shift_teal, '#1f7a72'),
    refreshed_banner: raw.refreshed_banner !== false,
    ebay_flat_shipping_usd: (() => {
      const amount = Number(raw.ebay_flat_shipping_usd);
      return Number.isFinite(amount) ? Math.min(200, Math.max(0, Math.round(amount * 100) / 100)) : 12;
    })(),
    refreshed_messages: (Array.isArray(raw.refreshed_messages) ? raw.refreshed_messages : [
      'Every device refreshed and tested by the seller',
      'Inspected, cleaned & tested before shipping',
    ]).map((item) => {
      if (typeof item === 'string') return item.trim().slice(0, 140);
      if (item && typeof item === 'object' && 'message' in item) return asString((item as { message?: unknown }).message).slice(0, 140);
      return '';
    }).filter(Boolean).slice(0, 8),
    ewaste_launch_mode: asString(raw.ewaste_launch_mode) === 'live' ? 'live' : 'waitlist',
    ewaste_partner_name: asString(raw.ewaste_partner_name).slice(0, 120),
    ewaste_phone: asString(raw.ewaste_phone).slice(0, 40),
    ewaste_response_time: asString(raw.ewaste_response_time).slice(0, 80),
    ewaste_year: asString(raw.ewaste_year).replace(/[^\d]/g, '').slice(0, 4),
  };
}

export function originOf(value: string): string {
  const safe = publicHttpsUrl(value);
  if (!safe) return '';
  return new URL(safe).origin;
}

export function buildCsp(options: { formOrigins: string[]; connectOrigins: string[]; imgHosts: string[]; scriptHosts?: string[]; scriptHashes?: string[] }): string {
  const img = ["'self'", 'data:', ...new Set(options.imgHosts.filter(Boolean))];
  const forms = ["'self'", 'https://www.paypal.com', 'mailto:', ...new Set(options.formOrigins.filter(Boolean))];
  const connect = ["'self'", ...new Set(options.connectOrigins.filter(Boolean))];
  const hashes = (options.scriptHashes ?? []).map((hash) => (hash.startsWith("'") ? hash : `'sha256-${hash}'`));
  const scriptHosts = [...new Set((options.scriptHosts ?? []).filter(Boolean))];
  return [
    "default-src 'self'",
    `script-src 'self'${scriptHosts.length ? ` ${scriptHosts.join(' ')}` : ''}${hashes.length ? ` ${hashes.join(' ')}` : ''}`,
    "style-src 'self'",
    "font-src 'self'",
    `img-src ${img.join(' ')}`,
    `connect-src ${connect.join(' ')}`,
    `form-action ${forms.join(' ')}`,
    "frame-src 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    'upgrade-insecure-requests',
  ].join('; ');
}

export function looksSensitive(message: string): boolean {
  const m = message.toLowerCase();
  if (/\b(password|passcode|passphrase|cvv|cvc|ssn|social security|routing|bank account|pin)\b/.test(m)) {
    return true;
  }
  const digits = message.replace(/\D/g, '');
  return digits.length >= 13 && digits.length <= 19 && /\d[\d\s-]{12,}/.test(message);
}

const STOP = new Set(['the', 'a', 'an', 'to', 'for', 'of', 'and', 'or', 'my', 'is', 'on', 'do', 'you', 'your', 'we', 'i', 'it', 'in', 'with', 'how', 'what', 'where', 'when', 'can', 'please']);

function tokens(value: string): string[] {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((word) => word.length > 2 && !STOP.has(word));
}

export function answerChat(message: string, faq: FaqItem[], products: { title: string; href: string; priceLabel: string; sample: boolean; haystack: string }[]): ChatReply {
  const cleaned = message.replace(/\s+/g, ' ').trim().slice(0, 500);
  if (!cleaned) {
    return { text: 'Ask about shipping, returns, payment, Tech Help, or a product.', links: [], confident: true };
  }
  if (looksSensitive(cleaned)) {
    return {
      text: 'Please do not send card numbers, bank details, or passwords here. This chat never asks for them. Pay only on the PayPal or Stripe page, and email the shop if an order needs a person.',
      links: [{ href: 'mailto:sales@earnitnotgiven.com', label: 'Email sales@earnitnotgiven.com' }],
      confident: true,
    };
  }

  const words = tokens(cleaned);
  let bestFaq: FaqItem | null = null;
  let faqScore = 0;
  for (const item of faq) {
    const hay = `${item.question} ${item.keywords.join(' ')} ${item.answer}`.toLowerCase();
    let score = 0;
    for (const word of words) {
      if (item.keywords.some((keyword) => keyword.toLowerCase().includes(word) || word.includes(keyword.toLowerCase()))) score += 2;
      else if (hay.includes(word)) score += 1;
    }
    if (score > faqScore) {
      faqScore = score;
      bestFaq = item;
    }
  }

  const ranked = products
    .map((product) => {
      const hay = product.haystack.toLowerCase();
      let score = 0;
      for (const word of words) if (hay.includes(word)) score += 1;
      return { product, score };
    })
    .filter((row) => row.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  const productScore = ranked[0]?.score ?? 0;
  if (bestFaq && faqScore >= 2 && faqScore >= productScore) {
    return { text: bestFaq.answer, links: [], confident: true };
  }
  if (ranked.length && productScore >= 1 && words.length) {
    const links = ranked.map(({ product }) => ({
      href: product.href,
      label: `${product.title} · ${product.priceLabel}${product.sample ? ' · Sample' : ''}`,
    }));
    return {
      text: 'These listings match what you typed. Sample items are placeholders and are not for sale.',
      links,
      confident: true,
    };
  }

  return {
    text: 'I am not sure about that. Email the shop and a person will answer, or send a Tech Help booking request.',
    links: [
      { href: 'mailto:sales@earnitnotgiven.com', label: 'Email sales@earnitnotgiven.com' },
      { href: '/tech-help', label: 'Book Tech Help' },
      { href: '/contact', label: 'Contact' },
    ],
    confident: false,
  };
}

export type PayLine = { name: string; amount: string; quantity: number; sku: string };

export function paypalLines(
  lines: { name: string; unitPrice: number; qty: number; sku: string }[],
  code: string,
  promos: PromoCode[],
): { lines: PayLine[]; subtotal: number; discount: number; total: number; applied: string } {
  const priced = lines.map((line) => ({
    ...line,
    qty: Math.max(1, Math.round(line.qty)),
    unitCents: Math.round(effectivePrice(line.unitPrice) * 100),
  }));
  const subtotalCents = priced.reduce((sum, line) => sum + line.unitCents * line.qty, 0);
  const match = promos.find((promo) => promo.active && promo.code.toUpperCase() === code.trim().toUpperCase() && promo.percent > 0);
  const discountCents = match ? Math.min(subtotalCents - 1, Math.round(subtotalCents * (match.percent / 100))) : 0;
  let remaining = discountCents;
  const discounted = priced.map((line, index) => {
    const extended = line.unitCents * line.qty;
    let cut = 0;
    if (discountCents > 0 && subtotalCents > 0) {
      cut = index === priced.length - 1 ? remaining : Math.floor((discountCents * extended) / subtotalCents);
      remaining -= cut;
    }
    return { ...line, extended: Math.max(0, extended - cut) };
  });

  const pay: PayLine[] = discounted.map((line) => {
    const baseName = line.name.replace(/\s+/g, ' ').trim().slice(0, 110);
    if (line.extended % line.qty === 0) {
      return {
        name: baseName,
        amount: (line.extended / line.qty / 100).toFixed(2),
        quantity: line.qty,
        sku: line.sku.slice(0, 127),
      };
    }
    return {
      name: `${baseName} (${line.qty})`.slice(0, 127),
      amount: (line.extended / 100).toFixed(2),
      quantity: 1,
      sku: line.sku.slice(0, 127),
    };
  });

  return {
    lines: pay,
    subtotal: subtotalCents / 100,
    discount: discountCents / 100,
    total: (subtotalCents - discountCents) / 100,
    applied: match && discountCents > 0 ? match.code : '',
  };
}

type GuideProduct = {
  slug: string;
  title: string;
  href: string;
  priceLabel: string;
  sample: boolean;
  image: string;
};

function renderInline(source: string): string {
  const re = /\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`/g;
  let html = '';
  let last = 0;
  for (const match of source.matchAll(re)) {
    const index = match.index ?? 0;
    html += escapeHtml(source.slice(last, index));
    if (match[1] && match[2]) {
      const href = safeUrl(match[2]);
      const text = escapeHtml(match[1]);
      if (!href) html += text;
      else if (isExternal(href)) {
        html += `<a href="${escapeHtml(href)}" rel="noopener noreferrer" target="_blank">${text}</a>`;
      } else {
        html += `<a href="${escapeHtml(href)}">${text}</a>`;
      }
    } else if (match[3]) html += `<strong>${escapeHtml(match[3])}</strong>`;
    else if (match[4]) html += `<em>${escapeHtml(match[4])}</em>`;
    else if (match[5]) html += `<code>${escapeHtml(match[5])}</code>`;
    last = index + match[0].length;
  }
  html += escapeHtml(source.slice(last));
  return html;
}

function productCard(product: GuideProduct): string {
  const flag = product.sample ? '<span class="flag">Sample</span>' : '';
  const img = product.image
    ? `<img src="${escapeHtml(product.image)}" alt="" width="640" height="480" />`
    : '';
  return `<article class="card embed-card"><a href="${escapeHtml(product.href)}">${img}${flag}<h3>${escapeHtml(product.title)}</h3></a><p class="price">${escapeHtml(product.priceLabel)}</p></article>`;
}

function affiliateCard(program: string, title: string, url: string, note: string, amazonTag: string): string {
  const safe = program === 'amazon' ? withAmazonTag(url, amazonTag) : safeUrl(url);
  const heading = escapeHtml(title || 'Affiliate placeholder');
  const detail = escapeHtml(note || 'Placeholder. No price or rating is shown here.');
  const link = safe
    ? `<a class="btn btn-ghost" href="${escapeHtml(safe)}" rel="sponsored nofollow noopener noreferrer" target="_blank">View on ${escapeHtml(program)}</a>`
    : '<p class="muted">Placeholder link. Add a real https affiliate URL before you publish this guide.</p>';
  return `<aside class="affiliate-card"><p class="eyebrow">Affiliate · ${escapeHtml(program)}</p><h3>${heading}</h3><p>${detail}</p>${link}</aside>`;
}

/** Renders a small markdown subset. Every piece of source text is escaped. */
export function renderRichText(markdown: string, ctx: { products: GuideProduct[]; amazonTag: string } ): string {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  const blocks: string[] = [];
  let para: string[] = [];
  let list: string[] = [];
  let listKind: 'ul' | 'ol' | '' = '';
  let code: string[] | null = null;

  const flushPara = () => {
    if (!para.length) return;
    blocks.push(`<p>${renderInline(para.join(' '))}</p>`);
    para = [];
  };
  const flushList = () => {
    if (!list.length || !listKind) return;
    blocks.push(`<${listKind}>${list.map((item) => `<li>${renderInline(item)}</li>`).join('')}</${listKind}>`);
    list = [];
    listKind = '';
  };

  for (const line of lines) {
    if (code) {
      if (line.trim().startsWith('```')) {
        blocks.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`);
        code = null;
      } else code.push(line);
      continue;
    }
    if (line.trim().startsWith('```')) {
      flushPara();
      flushList();
      code = [];
      continue;
    }
    const shortcode = line.trim().match(/^\[\[(product|affiliate):([^\]]+)\]\]$/);
    if (shortcode) {
      flushPara();
      flushList();
      if (shortcode[1] === 'product') {
        const slug = shortcode[2].trim();
        const product = ctx.products.find((item) => item.slug === slug);
        blocks.push(product ? productCard(product) : `<p class="muted">Product “${escapeHtml(slug)}” is not on the site.</p>`);
      } else {
        const [program = 'amazon', title = '', url = '', note = ''] = shortcode[2].split('|').map((part) => part.trim());
        blocks.push(affiliateCard(program || 'amazon', title, url, note, ctx.amazonTag));
      }
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushPara();
      flushList();
      const level = heading[1].length + 1;
      blocks.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      continue;
    }
    const bullet = line.match(/^\s*[-*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (bullet || ordered) {
      flushPara();
      const kind = bullet ? 'ul' : 'ol';
      if (listKind && listKind !== kind) flushList();
      listKind = kind;
      list.push((bullet || ordered)?.[1] ?? '');
      continue;
    }
    if (!line.trim()) {
      flushPara();
      flushList();
      continue;
    }
    flushList();
    para.push(line.trim());
  }
  if (code) blocks.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`);
  flushPara();
  flushList();
  return blocks.join('\n');
}

export function jsonForScript(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
}
