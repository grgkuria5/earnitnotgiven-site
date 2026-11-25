import { getCollection, type CollectionEntry } from 'astro:content';
import settingsJson from '../../data/settings.json';
import etsyJson from '../../data/etsy-products.json';
import servicesJson from '../../data/services.json';
import faqJson from '../../data/faq.json';
import bannersJson from '../../data/banners.json';
import picksJson from '../../data/affiliate-picks.json';
import reviewsJson from '../../data/reviews.json';
import categoriesJson from '../../data/categories.json';
import {
  amazonLink,
  buildCsp,
  effectivePrice,
  etsyLink,
  hostOf,
  money,
  normalizeSettings,
  originOf,
  publicHttpsUrl,
  safeUrl,
  type FaqItem,
  type Settings,
} from './pure';

export const settings: Settings = normalizeSettings(settingsJson);
export const SITE = 'https://www.earnitnotgiven.com';
export const AMAZON_DISCLOSURE = 'As an Amazon Associate I earn from qualifying purchases.';

export type CategoryNode = {
  id: string;
  label: string;
  blurb: string;
  tone: 'tech' | 'fashion';
  icon: string;
  hidden: boolean;
  kind: 'catalog' | 'link' | 'condition';
  href: string;
  google_taxonomy: string;
  conditions: string[];
  children: CategoryNode[];
};

const LEGACY_CATEGORY: Record<string, string> = {
  electronics: 'accessories',
  computers: 'computers',
  cellphones: 'phones',
  clothing: 'clothing',
  digital: 'wall-art',
};

function asNode(raw: Record<string, unknown>, fallbackTone: 'tech' | 'fashion'): CategoryNode {
  const id = String(raw.id || '').trim();
  const tone = raw.tone === 'fashion' ? 'fashion' : raw.tone === 'tech' ? 'tech' : fallbackTone;
  const kind = raw.kind === 'link' || raw.kind === 'condition' ? raw.kind : 'catalog';
  const children = Array.isArray(raw.children) ? raw.children.map((child) => asNode(child as Record<string, unknown>, tone)) : [];
  return {
    id,
    label: String(raw.label || id),
    blurb: String(raw.blurb || ''),
    tone,
    icon: String(raw.icon || 'tag'),
    hidden: raw.hidden === true,
    kind,
    href: String(raw.href || (kind === 'catalog' || kind === 'condition' ? `/shop/${id}` : '/shop')),
    google_taxonomy: String(raw.google_taxonomy || 'Electronics'),
    conditions: Array.isArray(raw.conditions) ? raw.conditions.map(String) : [],
    children: children.filter((child) => child.id),
  };
}

export const categories: CategoryNode[] = (Array.isArray(categoriesJson.categories) ? categoriesJson.categories : [])
  .map((row) => asNode(row as Record<string, unknown>, 'tech'))
  .filter((row) => row.id);

export function visibleCategories(): CategoryNode[] {
  return categories.filter((category) => !category.hidden);
}

export function allCategoryNodes(): CategoryNode[] {
  return categories.flatMap((category) => [category, ...category.children]);
}

export type ProductEntry = CollectionEntry<'products'>;
export type GuideEntry = CollectionEntry<'guides'>;

export function categoryById(id: string): CategoryNode | undefined {
  return allCategoryNodes().find((category) => category.id === id);
}

export function toneForCategory(id: string): 'tech' | 'fashion' {
  return categoryById(id)?.tone ?? categoryById(LEGACY_CATEGORY[id] || '')?.tone ?? 'tech';
}

export function googleTaxonomyFor(categoryId: string, subcategoryId = ''): string {
  return categoryById(subcategoryId)?.google_taxonomy || categoryById(categoryId)?.google_taxonomy || categoryById(LEGACY_CATEGORY[categoryId] || '')?.google_taxonomy || 'Electronics';
}

export function productInCategory(product: ProductEntry, node: CategoryNode): boolean {
  const category = product.data.category;
  const sub = product.data.subcategory || '';
  const legacy = LEGACY_CATEGORY[category] || '';
  if (node.kind === 'condition') return node.conditions.includes(product.data.condition);
  if (sub === node.id || category === node.id) return true;
  if (!sub && legacy === node.id) return true;
  return node.children.some((child) => child.id === sub || child.id === category || (!sub && child.id === legacy));
}

export async function allProducts(): Promise<ProductEntry[]> {
  const products = await getCollection('products');
  return products
    .filter((product) => !product.data.draft)
    .sort((a, b) => Number(b.data.featured) - Number(a.data.featured) || a.data.title.localeCompare(b.data.title));
}

export async function publishedGuides(): Promise<GuideEntry[]> {
  const guides = await getCollection('guides');
  return guides
    .filter((guide) => !guide.data.draft)
    .sort((a, b) => b.data.date.localeCompare(a.data.date));
}

export function priceOf(product: ProductEntry): number {
  return effectivePrice(product.data.price, product.data.sale_price);
}

export function productHref(product: ProductEntry): string {
  return `/product/${product.id}`;
}

type EtsyRaw = { title?: string; etsy_url?: string; from_price_usd?: number; image?: string; tags?: string[]; ai_assisted?: boolean };

export function etsyProducts() {
  const rows = Array.isArray(etsyJson.products) ? (etsyJson.products as EtsyRaw[]) : [];
  return rows
    .map((row) => {
      const url = etsyLink(row.etsy_url ?? '');
      const title = (row.title ?? '').trim();
      if (!url || !title) return null;
      const tags = Array.isArray(row.tags) ? row.tags.map(String) : [];
      const ai = Boolean(row.ai_assisted) || tags.some((tag) => /ai|artificial/i.test(tag)) || /\bai\b/i.test(title);
      const image = safeUrl(row.image ?? '');
      return {
        title,
        url,
        price: typeof row.from_price_usd === 'number' ? row.from_price_usd : null,
        image,
        tags,
        ai,
      };
    })
    .filter((row): row is NonNullable<typeof row> => row !== null);
}

export type AffiliateProgram = 'amazon' | 'newegg' | 'bestbuy' | 'bh' | 'other';

export function affiliatePicks() {
  const rows = Array.isArray(picksJson.picks) ? picksJson.picks : [];
  return rows
    .map((row) => {
      const item = row as { title?: string; url?: string; program?: string; blurb?: string; note?: string };
      const program = (item.program ?? 'other') as AffiliateProgram;
      const enabled =
        (program === 'amazon' && settings.amazon_associates_tag) ||
        (program === 'newegg' && settings.newegg_affiliate_id) ||
        (program === 'bestbuy' && settings.bestbuy_affiliate_id) ||
        (program === 'bh' && settings.bh_affiliate_id) ||
        (program === 'other' && settings.other_affiliate_id);
      const url = program === 'amazon' ? amazonLink(item.url ?? '') : publicHttpsUrl(item.url ?? '');
      if (!enabled || !url || !(item.title ?? '').trim()) return null;
      return {
        title: item.title!.trim(),
        url,
        program,
        blurb: (item.blurb ?? item.note ?? '').trim(),
      };
    })
    .filter((row): row is NonNullable<typeof row> => row !== null);
}

export function amazonEnabled(): boolean {
  return settings.amazon_associates_tag.length > 0;
}

export function otherAffiliatesEnabled(): boolean {
  return Boolean(
    settings.newegg_affiliate_id || settings.bestbuy_affiliate_id || settings.bh_affiliate_id || settings.other_affiliate_id,
  );
}

export function activeBanners() {
  const items = Array.isArray(bannersJson.items) ? bannersJson.items : [];
  return items.filter((item) => item && item.active !== false && item.text);
}

export function servicesData() {
  return {
    area_note: servicesJson.area_note,
    experience_note: servicesJson.experience_note,
    services: servicesJson.services,
  };
}

export function faqItems(): FaqItem[] {
  return (faqJson.items ?? []).map((item) => ({
    id: item.id,
    question: item.question,
    keywords: item.keywords ?? [],
    answer: item.answer,
  }));
}

export async function contentSecurityPolicy(): Promise<string> {
  const hosts = new Set<string>();
  for (const product of etsyProducts()) {
    const host = hostOf(product.image);
    if (host) hosts.add(host);
  }
  const products = await getCollection('products');
  for (const product of products) {
    for (const image of product.data.images) {
      const host = hostOf(image);
      if (host) hosts.add(host);
    }
  }
  const scriptHosts: string[] = [];
  const connectOrigins = [originOf(settings.chat_ai_endpoint)].filter(Boolean);
  if (settings.analytics_provider === 'cloudflare' && settings.analytics_token) {
    scriptHosts.push('https://static.cloudflareinsights.com');
    connectOrigins.push('https://cloudflareinsights.com');
  }
  if (settings.analytics_provider === 'goatcounter' && settings.analytics_token.endsWith('.goatcounter.com')) {
    scriptHosts.push('https://gc.zgo.at');
    connectOrigins.push(`https://${settings.analytics_token}`);
  }
  return buildCsp({
    formOrigins: [originOf(settings.form_endpoint), originOf(settings.newsletter_form_action)].filter(Boolean),
    connectOrigins,
    imgHosts: [...hosts],
    scriptHosts,
    scriptHashes: [],
  });
}

export type Review = {
  product: string;
  author: string;
  rating: number;
  text: string;
  photo: string;
  source: string;
};

export function reviewsFor(slug: string): Review[] {
  const rows = Array.isArray(reviewsJson.reviews) ? reviewsJson.reviews : [];
  return rows
    .map((row) => {
      const item = row as Partial<Review>;
      const text = (item.text ?? '').trim();
      const author = (item.author ?? '').trim();
      const rating = Number(item.rating);
      if (!text || !author || item.product !== slug || rating < 1 || rating > 5) return null;
      return {
        product: slug,
        author,
        rating,
        text,
        photo: safeUrl(item.photo ?? ''),
        source: (item.source ?? '').trim(),
      };
    })
    .filter((row): row is Review => row !== null);
}

export function guideProducts(products: ProductEntry[]) {
  return products.map((product) => ({
    slug: product.id,
    title: product.data.title,
    href: productHref(product),
    priceLabel: money(priceOf(product)),
    sample: product.data.sample,
    image: safeUrl(product.data.images[0] ?? ''),
  }));
}

export function chatCatalog(products: ProductEntry[]) {
  return products.map((product) => ({
    title: product.data.title,
    href: productHref(product),
    priceLabel: money(priceOf(product)),
    sample: product.data.sample,
    haystack: `${product.data.title} ${product.data.brand} ${product.data.tags.join(' ')} ${product.data.summary} ${product.data.category}`,
  }));
}

export const conditionSchema = [
  'New',
  'Open Box',
  'Refurbished',
  'Used - Like New',
  'Used - Good',
  'Used - Fair',
  'Digital',
] as const;

export function schemaCondition(condition: string): string {
  if (condition === 'New' || condition === 'Open Box') return 'https://schema.org/NewCondition';
  if (condition === 'Refurbished') return 'https://schema.org/RefurbishedCondition';
  return 'https://schema.org/UsedCondition';
}
