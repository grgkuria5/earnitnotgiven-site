# EarnItNotGiven Control Center

This runs on the AIDesktop only. It opens at `http://127.0.0.1:8765`. It is not part of the public website.

It drafts listings, promo posts, email replies, guides, a ship checklist, and description edits. It also shows Etsy orders when you connect your own Etsy app. Nothing is posted, emailed, or marked shipped until you click the button for that one action.

Ollama stays at `http://127.0.0.1:11434` unless you point `OLLAMA_HOST` at a private or Tailscale address. A public address is refused. This app does not change Ollama settings and it does not touch ComfyUI.

## First time on Windows

1. Install Python from python.org and check “Add python.exe to PATH”.
2. Install Ollama and leave `ollama serve` running. Pull a small model, for example `ollama pull llama3.2`.
3. In this folder, copy `.env.example` to `.env`.
4. Double-click `start.bat`.
5. Open http://127.0.0.1:8765

If Ollama is off, the page says so. Sample drafts stay on screen so you can see the layout. They are not saved.

## Etsy

1. Open https://www.etsy.com/developers/register and create an app for yourself.
2. Set the redirect URI to exactly `http://127.0.0.1:8765/callback`.
3. Put the keystring in `.env` as `ETSY_KEYSTRING`. If Etsy also shows a shared secret, put it in `ETSY_SHARED_SECRET`. Leave both only in `.env`.
4. Put your shop id in `ETSY_SHOP_ID` when you know it.
5. Click Connect Etsy in the Sales tab and approve the read of receipts and the ability to add tracking.
6. To mark one order shipped, type the tracking number, pick the carrier, check the confirm box, and click Submit tracking. Sample rows never go to Etsy.

## Printify, site orders, export

If `PRINTIFY_TOKEN` is set, the Sales tab can open your Printify shop. It does not place Printify orders. Log a site order with the form, or keep Stripe and PayPal CSV exports and import them later from the same data file. Export CSV downloads what is on this PC, including the sample rows, which are marked sample.

## Approve

Approve on a real draft writes a file. Listing and guide drafts are saved with `draft: true`, so the public site still hides them until you turn that off. If `GITHUB_TOKEN` is set, Approve and commit pushes that file to `grgkuria5/earnitnotgiven-site`. The token stays in `.env`.

## Shipping Station

Open the Shipping Station tab. A new paid order from an imported Stripe or PayPal CSV, a manual site order, or an Etsy receipt that is not using an Etsy label is filled in with the address and the weight and size preset for that SKU (`parcel-presets.example.json`). Copy that file into `data/parcel-presets.json` and edit it.

Rates come from Shippo, EasyPost, or ShipStation when the matching keys are in `.env`. Connect UPS and USPS in that carrier account. This program does not store those carrier passwords. With no key, the tab shows sample rates and will not buy.

**Buy label** is one click. It still refuses a rate over the per-label max or the daily cap. Both caps start at $25 and $100 in `data/shipping-settings.json` (created when you save settings). Set either cap to 0 and no purchase is allowed.

Auto-buy is off. Turn it on only if you want a label bought when the customer already paid for shipping, and only inside those caps. Every decision is appended to `data/shipping-log.jsonl`.

After a real purchase, `scripts/print-label.ps1` prints the 4x6 label to the Windows printer name you set (`label_printer`, PDF or ZPL for Rollo, Zebra, Brother QL, or a UPS thermal printer). The packing slip (logo, order number, items, quantity, your thank-you line, an optional order note, and a personal line) prints to `slip_printer`. The personal line is an Ollama draft until you approve it. Tracking is then sent to Etsy with the same confirm path as Sales, and a customer email is saved as a draft. The email is not sent.

Sample slips are at http://127.0.0.1:8765/packing-slip/sample

## Snap & List

This is the phone-to-listing pipeline for resale electronics. It runs on the AIDesktop. A phone on the same LAN, or on your Tailscale network, opens `http://<that-address>:8765/snap`. The page is a home-screen app: in the phone browser, use Add to Home Screen. The camera button uses the phone camera. Nothing on that page publishes a listing.

`start.bat` listens on all interfaces (`CONTROL_BIND=0.0.0.0`) so the phone can connect. Requests from public internet addresses are refused. Loopback, private LAN, and Tailscale `100.x` addresses are allowed.

Photos also land in `C:\Users\Hacking\EarnItNotGiven\Products\_inbox` if you point iCloud, OneDrive, or Syncthing there. The next time you open Snap & List, those files move into `Products\<SKU>\photos`. HEIC becomes JPG when Pillow and pillow-heif are installed (`py -3 -m pip install pillow pillow-heif`). If they are not installed, the original file is kept and the log says so.

The first photo starts identification. If Ollama has a vision model installed (`ollama pull llava` or `llama3.2-vision`), that model reads the photo. If it does not, the note you typed is kept and specs are not guessed. Spec Checker can still open the maker page from a service tag.

There is no eBay developer account. A price check opens the public sold-listings search and does not invent a price. Approve on a snap draft writes a site file and a ready-to-paste eBay text file for seller **workhard1140**. It does not publish or end an eBay listing.

## Electronics copied from eBay

`tools/ebay-import/import_ebay.py` reads the public seller page for workhard1140 only. It uses no login and no API key, and it waits between requests. Sold or ended listings drop off because the file is replaced with what is still active. A captcha or a block leaves the previous file alone.

Buy now is on by default. The card shows the item price, the flat shipping rate, and the total before the button. PayPal is charged the item amount plus that shipping amount. A Stripe Payment Link is optional and stays hidden until you paste one in the content manager. Also on eBay is the second link. The eBay listing stays posted.

When a site sale is recorded, the item becomes pending, Buy now turns off, a Shipping Station order is saved, and you get an ntfy message or an email draft that says to end the eBay listing yourself. The message includes the item link. Nothing in this program ends or edits the eBay listing.

Refresh eBay listings is a button in Snap & List. Payment received records a sale for an item id after you see it in PayPal. `schedule-ebay.ps1` can create a disabled daily task that only refreshes the file.

Notifications go to your ntfy topic (`NTFY_TOPIC`, server `NTFY_SERVER`) or a Home Assistant webhook (`HA_NOTIFY_URL`). The message has Looks good, continue and Skip. If neither is set, an email draft to gkuria175@gmail.com is saved and is not sent.

Continue cleans the photos (EXIF rotation, a plain-edge crop, a light resize). It does not remove scratches or hide wear. Ollama then drafts the title and description from your notes, or your notes are kept if Ollama is off. The site file is written with `draft: true` and `refreshed_tested: true`. An eBay paste file is saved under `drafts/`. You get a preview link. Approve publishes the site file (`draft: false`) and, when an unpublished offer exists, publishes that offer. Sample rows never publish.

Every step is appended to `data/pipeline-log.jsonl`.

## Daily task

`schedule-daily.ps1` does nothing until you run:

```
powershell -File schedule-daily.ps1 -Register
```

That creates a task and leaves it **disabled**. Enable it in Task Scheduler only when you want 8:00 drafts. The task writes drafts. It does not publish them.
