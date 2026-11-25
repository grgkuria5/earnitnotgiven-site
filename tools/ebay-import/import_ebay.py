#!/usr/bin/env python3
"""Read George Kuria's public eBay listings into data/ebay-products.json.

No login and no API key. One seller only: workhard1140.
Sold or ended listings disappear because each run replaces the list
with whatever is active. A block or a captcha does not wipe a previous file.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SELLER = "workhard1140"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "ebay-products.json"
UA = "EarnItNotGiven-listing-mirror/1.0 (+https://www.earnitnotgiven.com; sales@earnitnotgiven.com)"
FEEDS = [
    f"https://www.ebay.com/sch/i.html?_ssn={SELLER}&_rss=1&_ipg=50",
    f"https://www.ebay.com/sch/i.html?_ssn={SELLER}&_sop=10&_ipg=50",
]

GUESSES = [
    (("rtx", "gtx", "radeon", "graphics card", "gpu"), "parts", "gpus"),
    (("printer", "laserjet", "inkjet", "mfp"), "printers", ""),
    (("laptop", "notebook", "macbook", "latitude", "thinkpad", "elitebook", "chromebook"), "computers", "laptops"),
    (("all-in-one", "all in one", "imac"), "computers", "all-in-ones"),
    (("monitor", "ultrasharp", "display"), "computers", "monitors"),
    (("poweredge", "server", "workstation"), "computers", "servers"),
    (("desktop", "optiplex", "tower", "sff"), "computers", "desktops"),
    (("iphone",), "phones", "iphone"),
    (("ipad", "tablet"), "phones", "tablets"),
    (("galaxy", "pixel", "android"), "phones", "android"),
    (("router", "switch", "firewall", "ubiquiti", "cisco", "access point"), "networking", "routers"),
    (("charger", "cable", "keyboard", "mouse", "dock"), "accessories", ""),
]


def shipping_amount(category: str, subcategory: str) -> float:
    path = ROOT / "data" / "shipping-rates.json"
    rates = {}
    if path.is_file():
        try:
            rates = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            rates = {}
    for key in (subcategory, category, "default"):
        if key and isinstance(rates.get(key), (int, float)):
            return round(float(rates[key]), 2)
    return 12.0


def parse_delivery(note: str) -> float | None:
    """eBay now says 'Free delivery' or '+$X delivery', not only 'shipping'."""
    text = (note or "").lower()
    if "free delivery" in text or "free shipping" in text:
        return 0.0
    match = re.search(r"\+?\s*\$(\d+(?:\.\d{1,2})?)", note or "")
    if match and "delivery" in text:
        return round(float(match.group(1)), 2)
    return None


def delivery_phrase(text: str) -> str:
    free = re.search(r"free delivery", text, re.I)
    if free:
        return "Free delivery"
    paid = re.search(r"\+\$\d+(?:\.\d{2})?\s+delivery(?:\s+in\s+[\d–-]+\s+days)?", text, re.I)
    if paid:
        return paid.group(0)
    if re.search(r"free shipping", text, re.I):
        return "Free delivery"
    return ""


def listing(title: str, url: str, price, condition: str, image: str, shipping_note: str) -> dict:
    category, sub = guess_category(title)
    parsed = parse_delivery(shipping_note)
    electronics = category != "collectibles"
    return {
        "item_id": item_id(url),
        "title": title,
        "price": price,
        "condition": condition or "See the eBay listing",
        "image": image,
        "url": url.split("?")[0],
        "category": category,
        "subcategory": sub,
        "shipping_note": shipping_note,
        "shipping_usd": parsed if parsed is not None else shipping_amount(category, sub),
        "buy_direct": True,
        "stripe_payment_link": "",
        "status": "active",
        "refreshed_tested": electronics,
    }


def guess_category(title: str) -> tuple[str, str]:
    text = title.lower()
    if any(word in text for word in ("hoodie", "jersey", "oil painting", "bento", "panini", "football card")):
        return "collectibles", ""
    if any(word in text for word in ("printer", "laserjet", "inkjet")):
        return "printers", ""
    if any(word in text for word in ("power supply", "psu", "hot-swap")):
        return "computers", "servers"
    if "motherboard" in text:
        return "parts", "motherboards"
    whole_pc = any(word in text for word in ("optiplex", "latitude", "precision", "desktop", "laptop", "notebook"))
    if not whole_pc and any(word in text for word in ("core i", "processor", "cpu")):
        return "parts", "cpus"
    if not whole_pc and any(word in text for word in ("radeon", "geforce", "firepro", "graphics card")):
        return "parts", "gpus"
    if any(word in text for word in ("network card", "10gbe", "gateway", "edgemarc", "brocade", "sfp", "router")):
        if "cable" in text or "sfp" in text:
            return "networking", "network-cables"
        if "network card" in text or "10gbe" in text:
            return "networking", ""
        return "networking", "routers"
    if "gpib" in text or "ieee-488" in text:
        return "parts", ""
    if "dock" in text:
        return "accessories", "docks"
    if any(word in text for word in ("latitude", "laptop", "notebook")):
        return "computers", "laptops"
    if any(word in text for word in ("optiplex", "precision", "desktop", "sff", "tower")):
        return "computers", "desktops"
    return "computers", ""


def load_previous() -> dict:
    if not OUT.is_file():
        return {"seller": SELLER, "products": []}
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"seller": SELLER, "products": []}
    if not isinstance(data, dict):
        return {"seller": SELLER, "products": []}
    return data


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"user-agent": UA, "accept": "application/rss+xml, application/xml, text/html"})
    with urllib.request.urlopen(request, timeout=25) as response:
        body = response.read()
        final = response.geturl()
    if "splashui/captcha" in final or b"captcha" in body[:4000].lower():
        raise RuntimeError("eBay returned a captcha. The previous catalog file was left as it was.")
    return body


def item_id(url: str) -> str:
    match = re.search(r"/itm/(?:[^/]+/)?(\d{9,})", url)
    return match.group(1) if match else ""


def parse_rss(body: bytes) -> list[dict]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    rows = []
    for item in root.iter():
        if not str(item.tag).endswith("item"):
            continue
        title = link = image = ""
        price = None
        condition = ""
        shipping = "Shipping is calculated on eBay."
        for child in list(item):
            tag = str(child.tag).lower()
            text = (child.text or "").strip()
            if tag.endswith("title"):
                title = text
            elif tag.endswith("link"):
                link = text
            elif "price" in tag and text:
                match = re.search(r"(\d+(?:\.\d{2})?)", text.replace(",", ""))
                if match:
                    price = float(match.group(1))
            elif "condition" in tag and text:
                condition = text
            elif tag.endswith("description") and text:
                img = re.search(r"https://i\.ebayimg\.com/[^\"'\s]+", text)
                if img:
                    image = img.group(0)
                money = re.search(r"\$(\d+(?:,\d{3})*(?:\.\d{2})?)", text)
                if money and price is None:
                    price = float(money.group(1).replace(",", ""))
                phrase = delivery_phrase(text)
                if phrase:
                    shipping = phrase
        if title and link.startswith("https://www.ebay.com/itm/"):
            rows.append(listing(title, link, price, condition, image, shipping))
    return rows


def parse_html(body: bytes) -> list[dict]:
    text = body.decode("utf-8", "replace")
    if "captcha" in text[:5000].lower():
        raise RuntimeError("eBay returned a captcha. The previous catalog file was left as it was.")
    rows = []
    for match in re.finditer(r"https://www\.ebay\.com/itm/(\d{9,})", text):
        url = f"https://www.ebay.com/itm/{match.group(1)}"
        if any(row["url"] == url for row in rows):
            continue
        window = text[max(0, match.start() - 400) : match.end() + 400]
        title_match = re.search(r'alt="([^"]{8,180})"', window) or re.search(r">([^<]{8,180})</(?:span|h3|a)>", window)
        title = title_match.group(1).strip() if title_match else ""
        if not title or "shop on ebay" in title.lower():
            continue
        price_match = re.search(r"\$(\d+(?:,\d{3})*(?:\.\d{2})?)", window)
        image_match = re.search(r"https://i\.ebayimg\.com/[^\"'\s]+", window)
        rows.append(
            listing(
                title,
                url,
                float(price_match.group(1).replace(",", "")) if price_match else None,
                "See the eBay listing",
                image_match.group(0) if image_match else "",
                delivery_phrase(window) or "Shipping is calculated on eBay.",
            )
        )
        if len(rows) >= 50:
            break
    return rows


def merge(previous: list[dict], fresh: list[dict]) -> list[dict]:
    saved = {row.get("item_id"): row for row in previous if isinstance(row, dict)}
    merged = []
    for row in fresh:
        old = saved.get(row["item_id"]) or {}
        if "buy_direct" in old:
            row["buy_direct"] = bool(old.get("buy_direct"))
        if old.get("status") in {"pending", "sold"}:
            row["status"] = old["status"]
            row["buy_direct"] = False
        if isinstance(old.get("shipping_usd"), (int, float)):
            row["shipping_usd"] = round(float(old["shipping_usd"]), 2)
        if isinstance(old.get("stripe_payment_link"), str):
            row["stripe_payment_link"] = old["stripe_payment_link"]
        if old.get("refreshed_tested") is False:
            row["refreshed_tested"] = False
        merged.append(row)
    return merged


def main() -> int:
    previous = load_previous()
    if previous.get("seller") not in {None, "", SELLER}:
        print("Refusing to replace a file for a different seller.")
        return 1
    last_error = "No listing feed returned items."
    found: list[dict] = []
    for index, url in enumerate(FEEDS):
        if index:
            time.sleep(2)
        try:
            body = fetch(url)
        except urllib.error.HTTPError as exc:
            last_error = f"eBay responded {exc.code}. The previous catalog file was left as it was."
            print(last_error)
            return 2
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            print(last_error)
            return 2
        found = parse_rss(body) or parse_html(body)
        if found:
            break
    if not found:
        print(last_error)
        print("No active listings were written. If eBay blocked the read, supply data/ebay-products.json yourself.")
        return 2
    products = merge(previous.get("products") or [], found)
    OUT.write_text(
        json.dumps(
            {
                "seller": SELLER,
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "products": products,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(products)} active listings for {SELLER}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
