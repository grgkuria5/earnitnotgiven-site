# Earn It Not Given

Static shop for Earn It Not Given LLC, George's small business in Palo Alto. It is built to be hosted free on GitHub Pages at `www.earnitnotgiven.com`. There is no server to rent and no paid host.

Electronics, computers, phones, and clothing start as Sample placeholders. Delete those files when real items replace them. EarnItNotGiven designs (tees, leggings, jackets, posters, wall art) check out on Etsy. The design list lives in `data/etsy-products.json`.

## Run it on your PC

Install Node.js 22, then:

```
npm install
npm run dev
```

Open `http://127.0.0.1:43123`. `npm run build` writes the site into `dist/`.

## What you need to fill in

Edit `data/settings.json`, or use `/admin` after the OAuth step below.

| Setting | What to put |
| --- | --- |
| `paypal_business_email` | The email on your PayPal Business account. Checkout stays off until this is a real address. |
| Stripe link on each product | A Payment Link from your own Stripe account (`https://buy.stripe.com/...`). |
| `amazon_associates_tag` | Leave blank until Amazon approves you. Amazon Picks stay hidden, and the footer disclosure stays off. |
| `newegg_affiliate_id`, `bestbuy_affiliate_id`, `bh_affiliate_id`, `other_affiliate_id` | Leave blank until you have those programs. |
| `app_store_url` | Leave blank. GuardianOrbit shows Coming soon until this is an `https://apps.apple.com/...` link. |
| `form_endpoint` | Optional https URL for the contact and Tech Help forms (Formspree or FormSubmit). Blank means the form opens an email to sales@. |
| `newsletter_form_action` | Optional https URL for the email list (Mailchimp, Buttondown, or Formspree). Blank opens an email. Mailchimp often needs `newsletter_email_field` set to `EMAIL`. |
| `welcome_promo_code` | Shown on the site. Default `WELCOME10` takes 10% off the PayPal cart. Change the percent if you do not want that live. Stripe links do not use the code. |
| `active_theme` | `default`, `holiday`, or `sale`. |
| `chat_ai_endpoint` | Leave blank. See Chat below. |
| `/admin` sign-in | A GitHub personal access token in the browser. Never commit the token. |

Also replace Sample products, add your real photos, and paste Etsy listings into `data/etsy-products.json` (or the Etsy designs screen in `/admin`). The original product export was not in the project folder when this site was generated, so the designs grid is ready and empty.

The gold mark in the header is an original stand-in. Drop your logo file over `public/images/logo-mark.svg` (or replace the SVG in `src/components/Mark.astro`).

## Add a product

1. Open `/admin` (after the GitHub login below), choose Products, New product, and save. Or copy a markdown file in `src/content/products/`.
2. Set title, category, condition, price, quantity, and photos.
3. Leave `sample` off for a real item. Leave `draft` on if you are not ready for it to show.
4. Paste a Stripe Payment Link if you want a card button. PayPal uses the business email from settings and the cart.
5. `amazon_url` is your own Amazon seller listing. The Also on Amazon button shows only when that field is filled. Do not put an Associates link there.
6. Commit. GitHub Actions publishes the site.

For a spreadsheet, fill `tools/products-template.csv` and run:

```
py -3 tools/import-products.py
```

On Windows, `py -3` is the Python launcher. Rows whose SKU starts with `EXAMPLE` are skipped. The script only writes files. You still commit them yourself.

Columns include `amazon_url`, `digital`, `product_type` (`standard` or `bundle`), `bundle_items` (use `|` between items), and `bundle_savings`.

## Bundles, digital files, promos, themes

- A bundle is `product_type: bundle`, with `bundle_items` and an optional `bundle_savings` dollar amount for the badge. The price field is the bundle price.
- Digital downloads use category `digital` and `digital: true`. Say on the product how the file arrives: Stripe link, Etsy link (`etsy_delivery_url`), or email from you.
- Turn a code on under `promo_codes` in settings. The cart applies the percent on PayPal only. A code is not applied to a Stripe Payment Link.
- Change `active_theme` to `holiday` or `sale`, commit, and the next build switches the colors. Tech categories use a cool accent. Clothing, designs, and digital art use gold.

## Guides

Guides are markdown in `src/content/guides/`. Three starters are drafts (`draft: true`). They do not appear on the site or in the sitemap until you turn draft off.

On its own line:

- `[[product:sample-14-inch-ultrabook]]` embeds one of your products.
- `[[affiliate:amazon|Title|https://...|Note]]` embeds an affiliate card. Do not type a price or a star rating. The card says it is a placeholder until the URL is a real https link.

Every published guide shows: As an Amazon Associate I earn from qualifying purchases. Do not publish a guide until that sentence is true for your account.

## Tech Help

`/tech-help` lists PC setup, Wi-Fi, data transfer, virus cleanup, Windows reinstall, phone setup, and smart home. Prices ship as `Ask for quote`. Change the words in `/admin` under Tech Help. Do not invent a rate you have not decided.

The booking form emails `sales@earnitnotgiven.com` unless `form_endpoint` is an https address.

## Newsletter

The home page and the footer say “Get 10% off your first order” and show `WELCOME10`. Edit the message and the code in settings. The percent in `promo_codes` is what the PayPal cart actually takes off.

## Affiliate picks

`data/affiliate-picks.json` starts empty. A pick has `title`, `url`, `program` (`amazon`, `newegg`, `bestbuy`, `bh`, or `other`), and a short `blurb`. No prices and no ratings. The section stays hidden until the matching id in settings is filled. Links use `rel="sponsored nofollow noopener noreferrer"`.

## Chat

The gold bubble answers from `data/faq.json` and from product titles. Edit the FAQ in `/admin`. It offers email and Tech Help when it is unsure.

`chat_ai_endpoint` is optional. Leave it blank. If you later run your own https proxy in front of Ollama, put only that https address here. The site refuses localhost, so visitors cannot call your PC. Do not put an API key in the file. The chat does not ask for card numbers or passwords.

## AI lister

See `tools/ai-lister/README.md`. It is for your Windows PC and local Ollama only. Drafts land in `tools/ai-lister/review/`, which git ignores. Nothing is published until you copy a file into the catalog and commit it.

## Content manager (`/admin`)

The editor is [Sveltia CMS](https://github.com/sveltia/sveltia-cms), stored in this repo (not loaded from a CDN at runtime). It publishes by committing to GitHub as you.

GitHub has not shipped client-side PKCE for single-page apps, so this site does not put an OAuth client id or client secret in the repo. Sign-in is a GitHub personal access token that stays in your browser:

1. Open `https://www.earnitnotgiven.com/admin/`.
2. Choose Sign in with token.
3. GitHub’s link asks for a token that can read and write this repository (Contents: Read and write). Create it, paste it once, and do not commit it.
4. Only that token can save. A token without write access cannot publish.

`/admin` is disallowed in `robots.txt`. Anyone can open the login page. Nothing changes in git until a token with access to `grgkuria5/earnitnotgiven-site` is used. If you turn on “require a pull request” for `main`, either allow your user to bypass that rule or the editor cannot commit directly. See Security.

A full OAuth code flow needs a small authenticator you would host yourself (Sveltia’s Cloudflare worker). That is optional later. It is not required, and its secret must never be committed.

## Namecheap DNS

In the Namecheap advanced DNS for `earnitnotgiven.com`:

| Type | Host | Value |
| --- | --- | --- |
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `grgkuria5.github.io` |

This repo includes `CNAME` with `www.earnitnotgiven.com`. In the GitHub repo, Settings → Pages → Custom domain: `www.earnitnotgiven.com`, source: GitHub Actions. After the certificate is issued, turn on **Enforce HTTPS**.

GitHub redirects the apex (`earnitnotgiven.com`) to `www` when those four A records point at GitHub and the Pages domain is `www`.

## Security

- Enforce HTTPS on GitHub Pages after DNS works.
- Turn on two-factor authentication for your GitHub user.
- Protect `main` (require a pull request if you want a review, and remember the note above about `/admin`).
- Optional later step, only after you approve a DNS change: put the domain behind Cloudflare’s free proxy for WAF, DDoS filtering, and HSTS. That replaces the Namecheap records above with whatever Cloudflare gives you. Do not do this until you mean to move DNS.
- The storefront sends a strict Content-Security-Policy in a meta tag: scripts, styles, and fonts from this site only, images from this site plus any https image hosts actually used, PayPal for checkout, and the form or newsletter host only if you set one. `frame-ancestors` cannot be set from a meta tag. If you add Cloudflare, also send these headers: `Content-Security-Policy` (the same policy plus `frame-ancestors 'none'`), `Strict-Transport-Security: max-age=15552000; includeSubDomains`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- `/admin` allows the self-hosted editor, GitHub’s API, and the font files that editor already references on jsDelivr. Its script tag has Subresource Integrity. The storefront does not use that CDN.
- Forms and chat use a hidden honeypot field, a few-second wait before the button works, and a limit on how many sends the browser will accept in a short time. That is not a server firewall. A determined script can still POST to a form service if you configure one.
- PayPal cart totals are sent by the browser. That is how PayPal Standard works without a server. Stripe Payment Links keep the price on Stripe, which is the stronger option for a single item.
- `tools/scan-secrets.mjs` runs in GitHub Actions. It looks for private keys, Stripe secret keys, and GitHub or Slack tokens. `.gitignore` ignores `.env`, `.pem`, and `.key`. Do not commit them.
- A second GitHub Actions workflow builds the site, runs `npm audit`, the unit tests, the secret scan, an internal link check, and HTML validation.
- `/.well-known/security.txt` points reports to `sales@earnitnotgiven.com`.
- Dependabot opens weekly update PRs for npm and Actions.

## Flash deals, warranty, pickup, Google

- Categories live in `data/categories.json`. Add, rename, reorder, or hide them in `/admin` under Categories. Products use a category id and an optional subcategory id. The menu is a mega menu. Each landing page filters by brand, price, condition, and spec. Spec Checker suggests a category from the lookup you picked. The Google feed writes `g:google_product_category` from that tree.
- A flash deal is `flash_price`, `flash_start`, and `flash_end` on a product. Times are Pacific, like `2026-11-25T09:00`. The home strip and `/deals` show a countdown and hide the deal outside that window. PayPal uses `flash_price`. `flash_stripe_link` is the card link during the window. `flash_qty_limit` shows as “3 left”.
- `warranty_days` is 0, 30, or 90. An optional add-on has `warranty_addon_price` and `warranty_stripe_link`.
- `local_pickup: true` adds the Palo Alto appointment note. `pickup_stripe_link` is the no-shipping payment link. Details are on `/pickup`.
- `return_window_days` in settings is the number on `/returns`. Policies are templates. Read them before you rely on them. They are not legal advice.
- Reviews live in `data/reviews.json`. The list starts empty. Nothing is shown until you add a real review.
- `/feed.xml` is the Google Merchant Center product feed. Sample listings are left out. Add `gtin` when you have one.
- `google_site_verification` is the Search Console meta value. Leave it blank until Google gives it to you.
- Analytics stays off until you set `analytics_provider` to `cloudflare` or `goatcounter` and `analytics_token` to the Cloudflare beacon token or a `name.goatcounter.com` host. Both options are cookieless, so there is no cookie banner. Leave them blank if you do not want analytics.
- Search Console: add the property `https://www.earnitnotgiven.com`, use the meta tag, put the code in settings, and submit `https://www.earnitnotgiven.com/sitemap-index.xml`.
- Merchant Center: free listings, country United States, feed URL `https://www.earnitnotgiven.com/feed.xml`. Do not send sample products.
- Google Business Profile: create a service-area business for Tech Help in Palo Alto. Do not publish a street address you do not want public. The site only says Palo Alto.

## Control Center (your PC only)

The listing helper and the sales dashboard are one local app: `tools/control-center`. It talks to Ollama at `http://127.0.0.1:11434` on the AIDesktop. It does not change Ollama or ComfyUI. Setup is in `tools/control-center/README.md`.

## Contact

george@earnitnotgiven.com  
sales@earnitnotgiven.com
