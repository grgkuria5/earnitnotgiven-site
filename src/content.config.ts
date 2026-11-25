import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const condition = z.enum([
  'New',
  'Open Box',
  'Refurbished',
  'Used - Like New',
  'Used - Good',
  'Used - Fair',
  'Digital',
]);

const products = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/products' }),
  schema: z.object({
    title: z.string(),
    category: z.string().min(1),
    subcategory: z.string().default(''),
    condition,
    price: z.number().nonnegative(),
    sale_price: z.number().nonnegative().optional(),
    quantity: z.number().int().nonnegative(),
    featured: z.boolean().default(false),
    sample: z.boolean().default(false),
    draft: z.boolean().default(false),
    sku: z.string().default(''),
    brand: z.string().default(''),
    summary: z.string().default(''),
    specs: z.array(z.object({ name: z.string(), value: z.string() })).default([]),
    images: z.array(z.string()).default([]),
    stripe_payment_link: z.string().default(''),
    paypal_enabled: z.boolean().default(true),
    amazon_url: z.string().default(''),
    tags: z.array(z.string()).default([]),
    digital: z.boolean().default(false),
    product_type: z.enum(['standard', 'bundle']).default('standard'),
    bundle_items: z.array(z.string()).default([]),
    bundle_savings: z.number().nonnegative().optional(),
    etsy_delivery_url: z.string().default(''),
    ai_assisted: z.boolean().default(false),
    shipping_note: z.string().default(''),
    flash_price: z.number().nonnegative().optional(),
    flash_start: z.string().default(''),
    flash_end: z.string().default(''),
    flash_qty_limit: z.number().int().nonnegative().optional(),
    flash_stripe_link: z.string().default(''),
    warranty_days: z.coerce.number().pipe(z.union([z.literal(0), z.literal(30), z.literal(90)])).default(0),
    warranty_addon_price: z.number().nonnegative().optional(),
    warranty_stripe_link: z.string().default(''),
    local_pickup: z.boolean().default(false),
    pickup_stripe_link: z.string().default(''),
    gtin: z.string().default(''),
    refreshed_tested: z.boolean().default(false),
  }),
});

const guides = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/guides' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.string(),
    draft: z.boolean().default(true),
    tags: z.array(z.string()).default([]),
  }),
});

export const collections = { products, guides };
