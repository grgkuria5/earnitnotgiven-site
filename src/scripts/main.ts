import { answerChat, countdownLabel, paypalLines, paypalReady, type ChatReply, type FaqItem, type PromoCode } from '../lib/pure';

const CART_KEY = 'eing-cart-v1';

type CartLine = {
  slug: string;
  title: string;
  unitPrice: number;
  qty: number;
  maxQty: number;
  image: string;
  sample: boolean;
  digital: boolean;
  sku: string;
};

function readCart(): CartLine[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(CART_KEY) || '[]') as CartLine[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeCart(lines: CartLine[]) {
  localStorage.setItem(CART_KEY, JSON.stringify(lines));
  document.querySelectorAll('[data-cart-count]').forEach((node) => {
    node.textContent = String(lines.reduce((sum, line) => sum + line.qty, 0));
  });
}

function initNav() {
  const button = document.querySelector<HTMLButtonElement>('[data-nav-toggle]');
  const panel = document.querySelector<HTMLElement>('#site-nav');
  const catMenu = document.querySelector<HTMLDetailsElement>('[data-cat-menu]');
  button?.addEventListener('click', () => {
    const open = panel?.classList.toggle('open');
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (!open && catMenu) catMenu.open = false;
  });
  document.addEventListener('click', (event) => {
    if (!catMenu?.open) return;
    if (event.target instanceof Node && catMenu.contains(event.target)) return;
    catMenu.open = false;
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !catMenu?.open) return;
    catMenu.open = false;
    catMenu.querySelector('summary')?.focus();
  });
}


function initCatStrip() {
  const scroller = document.querySelector<HTMLElement>('[data-cat-strip]');
  if (!scroller) return;
  const amount = () => Math.max(180, Math.floor(scroller.clientWidth * 0.8));
  document.querySelector<HTMLButtonElement>('[data-cat-strip-prev]')?.addEventListener('click', () => {
    scroller.scrollBy({ left: -amount(), behavior: 'smooth' });
  });
  document.querySelector<HTMLButtonElement>('[data-cat-strip-next]')?.addEventListener('click', () => {
    scroller.scrollBy({ left: amount(), behavior: 'smooth' });
  });
}

function initCount() {
  writeCart(readCart());
}

function initAdd() {
  document.querySelectorAll<HTMLButtonElement>('[data-add-cart]').forEach((button) => {
    button.addEventListener('click', () => {
      const slug = button.dataset.slug || '';
      const title = button.dataset.title || 'Item';
      const unitPrice = Number(button.dataset.price || '0');
      const maxQty = Math.max(1, Number(button.dataset.max || '1'));
      const qtyInput = document.querySelector<HTMLInputElement>('[data-qty]');
      const qty = Math.min(maxQty, Math.max(1, Number(qtyInput?.value || '1')));
      const lines = readCart().filter((line) => line.slug !== slug);
      lines.push({
        slug,
        title,
        unitPrice,
        qty,
        maxQty,
        image: button.dataset.image || '',
        sample: button.dataset.sample === 'true',
        digital: button.dataset.digital === 'true',
        sku: button.dataset.sku || slug,
      });
      writeCart(lines);
      const note = document.querySelector('[data-added]');
      if (note) note.textContent = `${title} is in the cart.`;
    });
  });
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function initCartPage() {
  const root = document.querySelector<HTMLElement>('#cart-root');
  if (!root) return;
  const promos = JSON.parse(root.dataset.promos || '[]') as PromoCode[];
  const email = root.dataset.paypalEmail || '';
  const ready = root.dataset.paypalReady === 'true' && paypalReady(email);
  const status = el('p', 'form-note');
  const list = el('div', 'stack');
  const summary = el('div', 'buybox');
  root.replaceChildren(status, list, summary);

  const render = () => {
    const lines = readCart();
    list.replaceChildren();
    if (!lines.length) {
      status.textContent = 'Your cart is empty.';
      const shop = el('a', 'btn btn-gold', 'Browse the shop');
      shop.href = '/shop';
      summary.replaceChildren(shop);
      return;
    }
    const samples = lines.some((line) => line.sample);
    status.textContent = samples
      ? 'This cart has sample listings. Remove them before a real purchase. Checkout stays off while a sample is in the cart.'
      : ready
        ? 'PayPal charges the total below. Promo codes apply here, not on a Stripe Payment Link.'
        : 'Add your PayPal Business email in data/settings.json before checkout will turn on.';

    lines.forEach((line, index) => {
      const row = el('article', 'panel');
      const title = el('h3', '', line.title);
      const meta = el('p', 'muted', `${line.sample ? 'Sample · ' : ''}${line.unitPrice.toFixed(2)} each`);
      const qty = document.createElement('input');
      qty.type = 'number';
      qty.min = '1';
      qty.max = String(line.maxQty);
      qty.value = String(line.qty);
      qty.setAttribute('aria-label', `Quantity for ${line.title}`);
      qty.addEventListener('change', () => {
        const next = readCart();
        next[index].qty = Math.min(line.maxQty, Math.max(1, Number(qty.value || '1')));
        writeCart(next);
        render();
      });
      const remove = el('button', 'btn btn-ghost', 'Remove');
      remove.type = 'button';
      remove.addEventListener('click', () => {
        writeCart(readCart().filter((item) => item.slug !== line.slug));
        render();
      });
      row.append(title, meta, qty, remove);
      list.append(row);
    });

    const code = document.createElement('input');
    code.value = root.dataset.welcomeCode || '';
    code.setAttribute('aria-label', 'Promo code');
    code.autocomplete = 'off';
    const apply = el('button', 'btn btn-ghost', 'Apply code');
    apply.type = 'button';
    const priced = () =>
      paypalLines(
        readCart().map((line) => ({ name: line.title, unitPrice: line.unitPrice, qty: line.qty, sku: line.sku })),
        code.value,
        promos,
      );
    const totals = el('p');
    const formSlot = el('div');

    const paintTotals = () => {
      const quote = priced();
      totals.textContent = quote.applied
        ? `Subtotal ${quote.subtotal.toFixed(2)} · Code ${quote.applied} takes off ${quote.discount.toFixed(2)} · PayPal total ${quote.total.toFixed(2)}`
        : `PayPal total ${quote.total.toFixed(2)}`;
      formSlot.replaceChildren();
      if (!ready || samples) return;
      const form = document.createElement('form');
      form.method = 'post';
      form.action = 'https://www.paypal.com/cgi-bin/webscr';
      const hidden: Record<string, string> = {
        cmd: '_cart',
        upload: '1',
        business: email,
        currency_code: 'USD',
        charset: 'utf-8',
        no_shipping: readCart().every((line) => line.digital) ? '1' : '0',
        return: 'https://www.earnitnotgiven.com/cart',
        cancel_return: 'https://www.earnitnotgiven.com/cart',
      };
      quote.lines.forEach((line, i) => {
        const n = i + 1;
        hidden[`item_name_${n}`] = line.name;
        hidden[`amount_${n}`] = line.amount;
        hidden[`quantity_${n}`] = String(line.quantity);
        hidden[`item_number_${n}`] = line.sku;
      });
      Object.entries(hidden).forEach(([name, value]) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.append(input);
      });
      const submit = el('button', 'btn btn-gold', 'Checkout with PayPal');
      submit.type = 'submit';
      form.append(submit);
      formSlot.append(form);
    };
    apply.addEventListener('click', paintTotals);
    summary.replaceChildren(el('label', '', 'Promo code'), code, apply, totals, formSlot);
    paintTotals();
  };
  render();
}

function initBrowse() {
  const root = document.querySelector<HTMLElement>('[data-browse]');
  if (!root) return;
  const grid = root.querySelector<HTMLElement>('[data-grid]');
  if (!grid) return;
  root.querySelector('form')?.addEventListener('submit', (event) => event.preventDefault());
  const cards = [...grid.querySelectorAll<HTMLElement>('[data-item]')];
  const condition = root.querySelector<HTMLSelectElement>('[data-filter-condition]');
  const min = root.querySelector<HTMLInputElement>('[data-filter-min]');
  const max = root.querySelector<HTMLInputElement>('[data-filter-max]');
  const sort = root.querySelector<HTMLSelectElement>('[data-filter-sort]');
  const kind = root.querySelector<HTMLSelectElement>('[data-filter-type]');
  const brand = root.querySelector<HTMLSelectElement>('[data-filter-brand]');
  const spec = root.querySelector<HTMLSelectElement>('[data-filter-spec]');
  const query = root.querySelector<HTMLInputElement>('[data-filter-q]');
  const empty = root.querySelector<HTMLElement>('[data-empty]');
  const count = root.querySelector<HTMLElement>('[data-count]');
  const params = new URLSearchParams(location.search);
  if (query && params.get('q')) query.value = params.get('q') || '';

  const apply = () => {
    const q = (query?.value || '').trim().toLowerCase();
    const visible = cards.filter((card) => {
      const price = Number(card.dataset.price || '0');
      if (condition?.value && card.dataset.condition !== condition.value) return false;
      if (brand?.value && card.dataset.brand !== brand.value) return false;
      if (spec?.value && !(card.dataset.specs || '').split('|').includes(spec.value)) return false;
      if (kind?.value === 'bundle' && card.dataset.type !== 'bundle') return false;
      if (kind?.value === 'digital' && card.dataset.digital !== 'true') return false;
      if (min?.value && price < Number(min.value)) return false;
      if (max?.value && price > Number(max.value)) return false;
      if (q && !(card.dataset.search || '').toLowerCase().includes(q)) return false;
      return true;
    });
    const mode = sort?.value || 'featured';
    visible.sort((a, b) => {
      const pa = Number(a.dataset.price || '0');
      const pb = Number(b.dataset.price || '0');
      if (mode === 'price-asc') return pa - pb;
      if (mode === 'price-desc') return pb - pa;
      if (mode === 'name') return (a.dataset.title || '').localeCompare(b.dataset.title || '');
      return Number(b.dataset.featured || '0') - Number(a.dataset.featured || '0');
    });
    cards.forEach((card) => card.toggleAttribute('hidden', !visible.includes(card)));
    visible.forEach((card) => grid.append(card));
    if (count) count.textContent = `${visible.length} shown`;
    if (empty) empty.toggleAttribute('hidden', visible.length > 0);
  };
  [condition, min, max, sort, kind, query, brand, spec].forEach((node) => node?.addEventListener('input', apply));
  apply();
}

function initGallery() {
  const main = document.querySelector<HTMLImageElement>('[data-gallery-main]');
  if (!main) return;
  document.querySelectorAll<HTMLButtonElement>('[data-gallery-thumb]').forEach((button) => {
    button.addEventListener('click', () => {
      const src = button.dataset.src || '';
      if (src.startsWith('/') || src.startsWith('https://')) main.src = src;
      main.alt = button.dataset.alt || main.alt;
    });
  });
}

type StampStore = Record<string, number[]>;

function stamps(): StampStore {
  try {
    return JSON.parse(sessionStorage.getItem('eing-stamps') || '{}') as StampStore;
  } catch {
    return {};
  }
}

function allow(key: string, max: number, windowMs: number): boolean {
  const now = Date.now();
  const all = stamps();
  const recent = (all[key] || []).filter((time) => now - time < windowMs);
  if (recent.length >= max) {
    all[key] = recent;
    sessionStorage.setItem('eing-stamps', JSON.stringify(all));
    return false;
  }
  recent.push(now);
  all[key] = recent;
  sessionStorage.setItem('eing-stamps', JSON.stringify(all));
  return true;
}

function businessDaysOut(days: number): string {
  const date = new Date();
  let left = days;
  while (left > 0) {
    date.setDate(date.getDate() + 1);
    const day = date.getDay();
    if (day !== 0 && day !== 6) left -= 1;
  }
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

function initEwasteForm(form: HTMLFormElement) {
  const date = form.querySelector<HTMLInputElement>('input[name="preferred_date"]');
  if (date) date.min = businessDaysOut(2);
  const business = form.querySelector<HTMLElement>('[data-ewaste-business]');
  const businessInputs = [...(business?.querySelectorAll<HTMLInputElement>('input') ?? [])];
  const syncBusiness = () => {
    const on = form.querySelector<HTMLInputElement>('input[name="customer_type"]:checked')?.value === 'Business / organization';
    business?.toggleAttribute('hidden', !on);
    businessInputs.forEach((input) => {
      input.required = on;
      if (!on) input.value = '';
    });
  };
  form.querySelectorAll<HTMLInputElement>('input[name="customer_type"]').forEach((radio) => {
    radio.addEventListener('change', syncBusiness);
  });
  const certificate = form.querySelector<HTMLElement>('[data-ewaste-certificate]');
  const syncCertificate = () => {
    const value = form.querySelector<HTMLInputElement>('input[name="has_data"]:checked')?.value;
    const show = value === 'Yes' || value === 'Not sure';
    certificate?.toggleAttribute('hidden', !show);
    if (!show) {
      const box = certificate?.querySelector<HTMLInputElement>('input');
      if (box) box.checked = false;
    }
  };
  form.querySelectorAll<HTMLInputElement>('input[name="has_data"]').forEach((radio) => {
    radio.addEventListener('change', syncCertificate);
  });
}

function ewasteReady(form: HTMLFormElement, note: HTMLElement | null): boolean {
  const photos = form.querySelector<HTMLInputElement>('input[name="photos"]');
  const files = [...(photos?.files ?? [])];
  const allowed = /\.(jpe?g|png|heic|webp)$/i;
  if (files.length > 5 || files.some((file) => file.size > 10 * 1024 * 1024 || !allowed.test(file.name))) {
    if (note) note.textContent = form.dataset.error || 'Something went wrong. Please try again.';
    return false;
  }
  const categories = [...form.querySelectorAll<HTMLInputElement>('input[name="categories"]')];
  if (categories.length && !categories.some((box) => box.checked)) {
    categories[0].setCustomValidity('Choose at least one kind of item.');
    categories[0].reportValidity();
    categories[0].setCustomValidity('');
    return false;
  }
  if (!form.checkValidity()) {
    form.reportValidity();
    return false;
  }
  return true;
}

function initForms() {
  const now = String(Date.now());
  document.querySelectorAll<HTMLInputElement>('[data-opened-at]').forEach((input) => {
    input.value = now;
  });
  window.setTimeout(() => {
    document.querySelectorAll<HTMLButtonElement>('[data-arm]').forEach((button) => {
      button.disabled = false;
    });
  }, 3000);

  document.querySelectorAll<HTMLFormElement>('[data-guarded-form]').forEach((form) => {
    if (form.dataset.guardedForm === 'ewaste') initEwasteForm(form);
    form.addEventListener('submit', (event) => {
      if (form.dataset.passed === '1') return;
      event.preventDefault();
      const note = form.querySelector<HTMLElement>('[data-form-note]');
      const trap = form.querySelector<HTMLInputElement>('[name="company_website"], [name="website"]');
      const opened = Number(form.querySelector<HTMLInputElement>('[data-opened-at]')?.value || '0');
      if (trap && trap.value.trim()) {
        if (note) note.textContent = 'Thanks. If this was a real note, email sales@earnitnotgiven.com.';
        return;
      }
      if (!opened || Date.now() - opened < 3000) {
        if (note) note.textContent = 'Please wait a few seconds and try again.';
        return;
      }
      if (form.dataset.guardedForm === 'ewaste' && !ewasteReady(form, note)) return;
      const kind = form.dataset.guardedForm || 'form';
      if (!allow(kind, 3, 10 * 60 * 1000)) {
        if (note) note.textContent = 'That is enough requests for now. Email sales@earnitnotgiven.com if you still need help.';
        return;
      }
      const endpoint = form.dataset.endpoint || '';
      if (endpoint.startsWith('https://')) {
        form.dataset.passed = '1';
        form.action = endpoint;
        form.method = 'post';
        form.submit();
        return;
      }
      const email = form.dataset.mail || 'sales@earnitnotgiven.com';
      const data = new FormData(form);
      const skip = new Set(['company_website', 'website', 'form_opened_at']);
      const lines = [...data.entries()]
        .filter(([key, value]) => !skip.has(key) && !(value instanceof File && value.size === 0))
        .map(([key, value]) => `${key}: ${value instanceof File ? value.name : String(value)}`);
      location.href = `mailto:${email}?subject=${encodeURIComponent(form.dataset.subject || 'Website message')}&body=${encodeURIComponent(lines.join('\n'))}`;
      if (note) {
        const name = String(data.get('name') || '').trim();
        note.textContent = form.dataset.success
          ? form.dataset.success.replaceAll('{name}', name)
          : 'Your email app should open with this message. If it does not, write to sales@earnitnotgiven.com.';
      }
    });
  });
}

function initChat() {
  const launcher = document.querySelector<HTMLButtonElement>('[data-chat-open]');
  const panel = document.querySelector<HTMLElement>('#chat-panel');
  const log = document.querySelector<HTMLElement>('[data-chat-log]');
  const form = document.querySelector<HTMLFormElement>('[data-chat-form]');
  const input = document.querySelector<HTMLInputElement>('#chat-text');
  const send = document.querySelector<HTMLButtonElement>('[data-chat-send]');
  if (!launcher || !panel || !log || !form || !input || !send) return;

  let faq: FaqItem[] = [];
  let products: { title: string; href: string; priceLabel: string; sample: boolean; haystack: string }[] = [];
  const endpoint = panel.dataset.endpoint || '';
  let openedAt = 0;
  let loaded = false;
  const loadData = async () => {
    if (loaded) return;
    const response = await fetch('/chat-data.json');
    if (!response.ok) return;
    const data = (await response.json()) as { faq: FaqItem[]; products: typeof products };
    faq = data.faq || [];
    products = data.products || [];
    loaded = true;
  };

  const paint = (reply: ChatReply, mine = false) => {
    const bubble = el('div', mine ? 'bubble mine' : 'bubble');
    bubble.append(el('p', '', reply.text));
    if (reply.links.length) {
      const links = el('div', 'chat-links');
      reply.links.forEach((link) => {
        const anchor = el('a', '', link.label);
        anchor.href = link.href;
        if (link.href.startsWith('http') || link.href.startsWith('mailto:')) {
          anchor.rel = 'noopener noreferrer';
          if (link.href.startsWith('http')) anchor.target = '_blank';
        }
        links.append(anchor);
      });
      bubble.append(links);
    }
    log.append(bubble);
    log.scrollTop = log.scrollHeight;
  };

  const open = (force?: boolean) => {
    const show = force ?? panel.hasAttribute('hidden');
    panel.toggleAttribute('hidden', !show);
    launcher.setAttribute('aria-expanded', show ? 'true' : 'false');
    if (show && !openedAt) {
      openedAt = Date.now();
      void loadData();
      window.setTimeout(() => {
        send.disabled = false;
      }, 1500);
      if (!log.childElementCount) {
        paint({
          text: 'Ask about shipping, returns, payment, Tech Help, or a product. Do not send card numbers or passwords.',
          links: [],
          confident: true,
        });
      }
      input.focus();
    }
  };
  launcher.addEventListener('click', () => open());
  document.querySelectorAll<HTMLButtonElement>('[data-chat-suggest]').forEach((button) => {
    button.addEventListener('click', () => {
      input.value = button.dataset.chatSuggest || '';
      open(true);
    });
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const trap = form.querySelector<HTMLInputElement>('[name="company_website"]');
    if (trap?.value.trim()) return;
    if (!openedAt || Date.now() - openedAt < 1500) return;
    const message = input.value.trim();
    if (!message) return;
    await loadData();
    if (!allow('chat', 8, 60 * 1000)) {
      paint({ text: 'Slow down a moment, then ask again.', links: [], confident: true });
      return;
    }
    paint({ text: message, links: [], confident: true }, true);
    input.value = '';
    let reply = answerChat(message, faq, products);
    if (!reply.confident && endpoint.startsWith('https://')) {
      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ message }),
        });
        if (response.ok) {
          const data = (await response.json()) as { reply?: string };
          if (data.reply && !/[<>]/.test(data.reply)) {
            reply = { text: data.reply.slice(0, 1200), links: reply.links, confident: true };
          }
        }
      } catch {
        /* keep the local reply */
      }
    }
    paint(reply);
  });
}

function initFlash() {
  const deals = [...document.querySelectorAll<HTMLElement>('[data-flash-end]')];
  if (!deals.length) return;
  const tick = () => {
    const now = Date.now();
    deals.forEach((deal) => {
      const start = Number(deal.dataset.flashStart || '0');
      const end = Number(deal.dataset.flashEnd || '0');
      const live = start > 0 && end > start && now >= start && now < end;
      const offer = deal.dataset.flashMode === 'offer';
      if (!offer) deal.toggleAttribute('hidden', !live);
      deal.querySelectorAll<HTMLElement>('.flash-offer').forEach((node) => node.toggleAttribute('hidden', !live));
      deal.querySelectorAll<HTMLElement>('.regular-price').forEach((node) => node.toggleAttribute('hidden', live));
      const timer = deal.querySelector<HTMLElement>('[data-countdown]');
      if (timer) timer.textContent = live ? `Ends in ${countdownLabel(end - now)} PT` : '';
      const price = live ? deal.dataset.flashPrice || '' : '';
      deal.querySelectorAll<HTMLButtonElement>('[data-add-cart]').forEach((button) => {
        button.dataset.price = price || button.dataset.regularPrice || button.dataset.price || '';
      });
      const amount = deal.querySelector<HTMLInputElement>('input[name="amount"]');
      if (amount) amount.value = Number(price || amount.dataset.regularAmount || amount.value).toFixed(2);
      const stripe = deal.dataset.flashStripe || '';
      const link = deal.querySelector<HTMLAnchorElement>('[data-stripe]');
      if (link) link.href = live && stripe.startsWith('https://') ? stripe : link.dataset.regularHref || link.href;
    });
    document.querySelectorAll<HTMLElement>('[data-flash-strip]').forEach((strip) => {
      const any = strip.querySelector('[data-flash-end]:not([hidden])');
      strip.toggleAttribute('hidden', !any);
    });
  };
  tick();
  window.setInterval(tick, 1000);
}

function initRefresh() {
  const root = document.querySelector<HTMLElement>('[data-refresh-splash]');
  if (!root) return;
  const lines = [...root.querySelectorAll<HTMLElement>('[data-refresh-line]')];
  if (lines.length < 2) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  let index = 0;
  window.setInterval(() => {
    lines[index].hidden = true;
    index = (index + 1) % lines.length;
    lines[index].hidden = false;
  }, 4200);
}

initRefresh();
initFlash();
initNav();
initCatStrip();
initCount();
initAdd();
initCartPage();
initBrowse();
initGallery();
initForms();
initChat();
