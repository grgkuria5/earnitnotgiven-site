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

## Daily task

`schedule-daily.ps1` does nothing until you run:

```
powershell -File schedule-daily.ps1 -Register
```

That creates a task and leaves it **disabled**. Enable it in Task Scheduler only when you want 8:00 drafts. The task writes drafts. It does not publish them.
