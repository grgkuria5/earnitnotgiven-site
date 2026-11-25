import { allProducts, chatCatalog, etsyProducts, faqItems } from '../lib/site';
import { money } from '../lib/pure';

export async function GET() {
  const products = [
    ...chatCatalog(await allProducts()),
    ...etsyProducts().map((design) => ({
      title: design.title,
      href: design.url,
      priceLabel: design.price !== null ? `From ${money(design.price)}` : 'On Etsy',
      sample: false,
      haystack: `${design.title} ${design.tags.join(' ')} etsy design`,
    })),
  ];
  return new Response(JSON.stringify({ faq: faqItems(), products }), {
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'public, max-age=300',
      'x-content-type-options': 'nosniff',
    },
  });
}
