#!/usr/bin/env python3
"""Refresh Etsy and eBay listing JSON from live sources. Never invent prices or URLs.

Etsy: Printify API (token from PRINTIFY_TOKEN or PRINTIFY_TOKEN_FILE).
eBay: public seller pages/feeds when they answer; otherwise keep the
      existing verified catalog in data/ebay-products.json.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ETSY_FILE = ROOT / "data" / "etsy-products.json"
EBAY_FILE = ROOT / "data" / "ebay-products.json"
PRINTIFY_API = "https://api.printify.com/v1"
AI_RE = re.compile(
    r"AI[- ]generated|AI[- ]assisted|created (with|using) AI|made with AI|AI art|artificial intelligence",
    re.I,
)
LISTING_RE = re.compile(r"https://www\.etsy\.com/listing/(\d+)", re.I)
EBAY_ITEM_RE = re.compile(r"https://www\.ebay\.com/itm/(\d+)", re.I)

TOKEN_PLACEHOLDERS = (
    Path("/workspace/.secrets/printify_token"),
    ROOT / ".secrets" / "printify_token",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_token() -> str:
    env = os.environ.get("PRINTIFY_TOKEN", "").strip()
    if env:
        return env
    path = os.environ.get("PRINTIFY_TOKEN_FILE", "").strip()
    candidates = [Path(path)] if path else []
    candidates.extend(TOKEN_PLACEHOLDERS)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip()
    raise SystemExit(
        "No Printify token. Set PRINTIFY_TOKEN or PRINTIFY_TOKEN_FILE, "
        "or place the token at /workspace/.secrets/printify_token."
    )


def redact(text: str, token: str) -> str:
    return text.replace(token, "***") if token else text


def get_json(url: str, headers: dict, token: str = "", timeout: int = 60):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = redact(err.read().decode("utf-8", "replace")[:240], token)
        return err.code, body
    except Exception as err:
        return 0, redact(str(err)[:240], token)


def etsy_url(handle: str, external_id: str) -> tuple[str, str]:
    handle = (handle or "").strip()
    ext = str(external_id or "").strip()
    match = LISTING_RE.search(handle)
    if match:
        listing_id = match.group(1)
        return f"https://www.etsy.com/listing/{listing_id}", listing_id
    if ext.isdigit():
        return f"https://www.etsy.com/listing/{ext}", ext
    return "", ""


def classify(title: str, previous: dict) -> tuple[str, str]:
    if previous.get("category") or previous.get("subcategory"):
        return previous.get("category") or "", previous.get("subcategory") or ""
    text = title.lower()
    if any(word in text for word in ("legging", "yoga pant")):
        return "clothing", "leggings"
    if any(word in text for word in ("bomber", "jacket")):
        return "clothing", "jackets"
    if any(word in text for word in ("hoodie", "hooded")):
        return "clothing", "hoodies"
    if any(word in text for word in ("tee", "t-shirt", "tshirt", "v-neck", "shirt")):
        return "clothing", "tees"
    if any(word in text for word in ("poster", "wall art", "print", "download")):
        return "wall-art", ""
    return "", ""


def refresh_etsy(token: str) -> int:
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "EarnItNotGiven-listings-refresh",
        "Accept": "application/json",
    }
    code, shops = get_json(f"{PRINTIFY_API}/shops.json", headers, token)
    if code != 200 or not isinstance(shops, list) or not shops:
        raise SystemExit(f"Printify shops error {code}: {redact(str(shops)[:200], token)}")
    etsy_shops = [shop for shop in shops if str(shop.get("sales_channel", "")).lower() == "etsy"] or shops
    shop_id = etsy_shops[0]["id"]

    previous = {}
    if ETSY_FILE.exists():
        raw = json.loads(ETSY_FILE.read_text(encoding="utf-8"))
        rows = raw.get("products", raw) if isinstance(raw, dict) else raw
        for row in rows or []:
            previous[str(row.get("etsy_listing_id", ""))] = row

    products = []
    page = 1
    while page < 12:
        code, payload = get_json(
            f"{PRINTIFY_API}/shops/{shop_id}/products.json?limit=50&page={page}",
            headers,
            token,
        )
        if code != 200 or not isinstance(payload, dict):
            raise SystemExit(f"Printify products error {code}: {redact(str(payload)[:200], token)}")
        products.extend(payload.get("data") or [])
        if page >= (payload.get("last_page") or 1):
            break
        page += 1

    out = []
    skipped = 0
    for product in products:
        if not product.get("visible"):
            continue
        external = product.get("external") or {}
        url, listing_id = etsy_url(external.get("handle") or "", external.get("id") or "")
        title = (product.get("title") or "").strip()
        variants = [v for v in (product.get("variants") or []) if v.get("is_enabled")]
        prices = [v.get("price") for v in variants if isinstance(v.get("price"), (int, float))]
        images = product.get("images") or []
        image = (images[0].get("src") if images else "") or ""
        if not url or not listing_id or not title or not prices:
            skipped += 1
            continue
        tags = [str(tag) for tag in (product.get("tags") or []) if str(tag).strip()]
        description = product.get("description") or ""
        ai = bool(AI_RE.search(description)) or any(AI_RE.search(tag) for tag in tags)
        category, subcategory = classify(title, previous.get(listing_id) or {})
        out.append({
            "title": title,
            "etsy_listing_id": listing_id,
            "etsy_url": url,
            "from_price_usd": round(min(prices) / 100, 2),
            "image": image,
            "tags": tags,
            "ai_assisted": ai,
            "category": category,
            "subcategory": subcategory,
        })

    if not out:
        raise SystemExit("No publishable Etsy listings came back from Printify.")

    ETSY_FILE.write_text(
        json.dumps(
            {
                "fetched_at": now_iso(),
                "source": "Printify API, Etsy-published products only",
                "products": out,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"etsy: wrote {len(out)} listings to {ETSY_FILE.relative_to(ROOT)} (skipped {skipped})")
    return len(out)


def refresh_ebay() -> int:
    existing = {"seller": "workhard1140", "fetched_at": "", "source": "", "products": []}
    if EBAY_FILE.exists():
        existing = json.loads(EBAY_FILE.read_text(encoding="utf-8"))
    products = list(existing.get("products") or [])
    active = [
        item
        for item in products
        if item.get("status") == "active"
        and item.get("title")
        and item.get("url")
        and isinstance(item.get("price"), (int, float))
        and EBAY_ITEM_RE.search(str(item.get("url") or ""))
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EarnItNotGivenBot/1.0)",
        "Accept": "application/rss+xml, application/xml, text/html, */*",
    }
    feeds = [
        "https://www.ebay.com/sch/i.html?_ssn=workhard1140&_rss=1",
        "https://www.ebay.com/sch/workhard1140/m.html?_rss=1",
    ]
    found_ids: set[str] = set()
    for url in feeds:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                body = response.read().decode("utf-8", "replace")
        except Exception as err:
            print(f"ebay: public fetch failed for {url} ({type(err).__name__})")
            continue
        if "Error Page | eBay" in body or len(body) < 500:
            print(f"ebay: public feed blocked or empty ({url})")
            continue
        found_ids.update(EBAY_ITEM_RE.findall(body))
        print(f"ebay: public feed returned {len(EBAY_ITEM_RE.findall(body))} item ids")

    if found_ids:
        kept = [item for item in active if str(item.get("item_id")) in found_ids]
        missing = [item["item_id"] for item in active if str(item.get("item_id")) not in found_ids]
        # Only drop items when the public feed clearly listed others; never invent replacements.
        existing["products"] = kept or active
        existing["fetched_at"] = now_iso()
        existing["source"] = "public eBay feed, unmatched existing rows dropped" if kept else existing.get("source")
        if missing and kept:
            print(f"ebay: dropped {len(missing)} ids not present on the public feed")
        EBAY_FILE.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        print(f"ebay: wrote {len(existing['products'])} verified listings")
        return len(existing["products"])

    print(
        f"ebay: public pages were blocked; keeping {len(active)} existing "
        "verified listings from data/ebay-products.json (site catalog / prior public export)"
    )
    return len(active)


def main() -> int:
    token = load_token()
    try:
        etsy_count = refresh_etsy(token)
        ebay_count = refresh_ebay()
    except SystemExit:
        raise
    except Exception as err:
        raise SystemExit(redact(str(err), token)) from None
    print(f"done: {etsy_count} Etsy, {ebay_count} eBay")
    return 0


if __name__ == "__main__":
    sys.exit(main())
