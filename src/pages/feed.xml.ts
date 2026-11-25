import type { APIRoute } from 'astro';
import { allProducts, googleTaxonomyFor, productHref, settings, SITE } from '../lib/site';
import { effectivePrice } from '../lib/pure';

function xml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function googleCondition(condition: string): string {
  if (condition === 'New' || condition === 'Open Box' || condition === 'Digital') return 'new';
  if (condition === 'Refurbished') return 'refurbished';
  return 'used';
}

export const GET: APIRoute = async () => {
  const products = (await allProducts()).filter((product) => !product.data.sample && product.data.quantity >= 0);
  const items = products
    .map((product) => {
      const price = effectivePrice(product.data.price, product.data.sale_price);
      const image = product.data.images[0] || '/images/og.png';
      const imageUrl = image.startsWith('http') ? image : new URL(image, SITE).toString();
      const gtin = (product.data.gtin || '').replace(/\D/g, '');
      const idExists = gtin ? 'yes' : 'no';
      return `    <item>
      <g:id>${xml(product.data.sku || product.id)}</g:id>
      <g:title>${xml(product.data.title)}</g:title>
      <g:description>${xml(product.data.summary || product.data.title)}</g:description>
      <g:link>${xml(new URL(productHref(product), SITE).toString())}</g:link>
      <g:image_link>${xml(imageUrl)}</g:image_link>
      <g:availability>${product.data.quantity > 0 ? 'in_stock' : 'out_of_stock'}</g:availability>
      <g:price>${price.toFixed(2)} USD</g:price>
      <g:condition>${googleCondition(product.data.condition)}</g:condition>
      <g:brand>${xml(product.data.brand || settings.business_name)}</g:brand>
      <g:google_product_category>${xml(googleTaxonomyFor(product.data.category, product.data.subcategory))}</g:google_product_category>
      ${gtin ? `<g:gtin>${xml(gtin)}</g:gtin>` : ''}
      <g:identifier_exists>${idExists}</g:identifier_exists>
    </item>`;
    })
    .join('\n');
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>${xml(settings.business_name)}</title>
    <link>${SITE}</link>
    <description>${xml(settings.tagline)} Sample listings are left out of this feed.</description>
${items}
  </channel>
</rss>`;
  return new Response(body, { headers: { 'content-type': 'application/xml; charset=utf-8' } });
};
