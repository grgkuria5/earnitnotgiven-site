"""Mark a site sale pending. Never calls eBay."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "data" / "ebay-products.json"
CONTROL = ROOT / "tools" / "control-center"
REMINDER = "End this listing on eBay to avoid double-selling"
SELLER = "workhard1140"


def reminder_text(item: dict) -> str:
    return "\n".join(
        [
            REMINDER,
            str(item.get("url") or ""),
            f"Seller {SELLER} stays as it is. This program did not end or edit the eBay listing.",
            f"Site order {item.get('item_id')} is pending. Pack it from the Shipping Station.",
        ]
    )


def mark_pending(catalog: dict, item_id: str) -> dict | None:
    products = catalog.get("products") if isinstance(catalog, dict) else None
    if not isinstance(products, list):
        return None
    for item in products:
        if str(item.get("item_id")) != str(item_id):
            continue
        if item.get("status") in {"pending", "sold"}:
            return item
        item["status"] = "pending"
        item["buy_direct"] = False
        return item
    return None


def record_site_sale(item_id: str, env: dict | None = None) -> dict:
    env = env or {}
    if not CATALOG.is_file():
        return {"ok": False, "message": "No eBay catalog file on this PC."}
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if catalog.get("seller") not in {None, "", SELLER}:
        return {"ok": False, "message": "Refusing a catalog for a different seller."}
    before = json.dumps(catalog)
    item = mark_pending(catalog, item_id)
    if not item:
        return {"ok": False, "message": "That item is not in the site catalog."}
    if before == json.dumps(catalog):
        return {"ok": True, "message": "Already pending. The eBay listing was not changed.", "ebay_url": item.get("url")}
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    order = {
        "order_id": f"SITE-{item_id}",
        "source": "site",
        "sample": False,
        "status": "paid-pending",
        "to_name": "",
        "items": [{"title": item.get("title"), "qty": 1, "sku": item_id}],
        "note": reminder_text(item),
        "ebay_url": item.get("url"),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    folder = CONTROL / "data"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "shipments.json"
    rows = []
    if path.is_file():
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rows = []
    if not any(row.get("order_id") == order["order_id"] for row in rows):
        rows.append(order)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    _alert(env, item)
    log = folder / "pipeline-log.jsonl"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"action": "site-sale-pending", "item_id": item_id, "ebay_changed": False}) + "\n")
    return {"ok": True, "message": reminder_text(item), "ebay_url": item.get("url")}


def _alert(env: dict, item: dict) -> None:
    text = reminder_text(item)
    topic = env.get("NTFY_TOPIC", "")
    if topic:
        import urllib.request

        server = env.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
        request = urllib.request.Request(
            f"{server}/{topic}",
            data=text.encode(),
            headers={"title": "End the eBay listing", "click": str(item.get("url") or "")},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                response.read()
            return
        except Exception:
            pass
    draft = CONTROL / "drafts" / f"end-ebay-{item.get('item_id')}.txt"
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(f"DRAFT — not sent\nTo: gkuria175@gmail.com\nSubject: End this eBay listing\n\n{text}\n", encoding="utf-8")
