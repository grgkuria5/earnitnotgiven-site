import { allProducts, chatCatalog, faqItems } from '../lib/site';

export async function GET() {
  const products = await allProducts();
  return new Response(JSON.stringify({ faq: faqItems(), products: chatCatalog(products) }), {
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'public, max-age=300',
      'x-content-type-options': 'nosniff',
    },
  });
}
