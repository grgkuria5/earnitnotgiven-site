"""Shipping Station. Buys a label only on a click, or under caps when auto-buy is on."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

DEFAULT_SETTINGS = {
    "auto_buy": False,
    "per_label_max_usd": 25.0,
    "daily_cap_usd": 100.0,
    "label_printer": "",
    "slip_printer": "",
    "label_format": "PDF",
    "thank_you": "Thank you for buying from Earn It Not Given. Every electronic is checked by hand in Palo Alto. If something is wrong, write sales@earnitnotgiven.com and George will answer.",
    "from_name": "Earn It Not Given LLC",
    "from_street": "",
    "from_city": "Palo Alto",
    "from_state": "CA",
    "from_zip": "94303",
}

SAMPLE_SHIPMENT = {
    "sample": True,
    "order_id": "SAMPLE-1001",
    "source": "Etsy sample",
    "customer_paid_shipping": True,
    "to_name": "Sample Buyer",
    "to_street": "1 Sample Street",
    "to_city": "Palo Alto",
    "to_state": "CA",
    "to_zip": "94301",
    "items": [{"sku": "SAMPLE-TEE", "title": "SAMPLE Orbit tee", "qty": 1, "weight_oz": 8, "length_in": 10, "width_in": 8, "height_in": 1}],
    "note": "",
    "personal_note": "",
}

SAMPLE_RATES = [
    {"id": "SAMPLE-USPS", "carrier": "USPS", "service": "Ground Advantage", "amount": 6.4, "sample": True},
    {"id": "SAMPLE-UPS", "carrier": "UPS", "service": "Ground", "amount": 9.15, "sample": True},
]


def load_settings() -> dict:
    path = DATA / "shipping-settings.json"
    saved = {}
    if path.is_file():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            saved = {}
    merged = dict(DEFAULT_SETTINGS)
    if isinstance(saved, dict):
        merged.update({key: saved[key] for key in DEFAULT_SETTINGS if key in saved})
    merged["auto_buy"] = bool(merged.get("auto_buy"))
    merged["per_label_max_usd"] = float(merged.get("per_label_max_usd") or 0)
    merged["daily_cap_usd"] = float(merged.get("daily_cap_usd") or 0)
    return merged


def save_settings(updates: dict) -> dict:
    current = load_settings()
    for key in DEFAULT_SETTINGS:
        if key in updates:
            current[key] = updates[key]
    current["auto_buy"] = bool(current.get("auto_buy"))
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "shipping-settings.json").write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current


def log_path() -> Path:
    return DATA / "shipping-log.jsonl"


def append_log(event: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with log_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def spent_today() -> float:
    path = log_path()
    if not path.is_file():
        return 0.0
    today = datetime.now(timezone.utc).date().isoformat()
    total = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("action") == "purchased" and str(row.get("at", "")).startswith(today):
            total += float(row.get("amount") or 0)
    return round(total, 2)


def decide(amount: float, settings: dict, *, auto: bool, customer_paid_shipping: bool, sample: bool) -> tuple[bool, str]:
    if sample:
        return False, "Sample rate. No label was bought."
    if amount <= 0:
        return False, "Rate is missing."
    cap = float(settings.get("per_label_max_usd") or 0)
    daily = float(settings.get("daily_cap_usd") or 0)
    if cap <= 0 or daily <= 0:
        return False, "Set a per-label max and a daily cap before any label can be bought."
    if amount > cap:
        return False, f"Rate ${amount:.2f} is over the ${cap:.2f} per-label max."
    used = spent_today()
    if used + amount > daily:
        return False, f"Daily cap ${daily:.2f} would be passed (${used:.2f} already spent)."
    if auto and not settings.get("auto_buy"):
        return False, "Auto-buy is off."
    if auto and not customer_paid_shipping:
        return False, "Auto-buy only runs when the customer paid for shipping."
    return True, "Within caps."


def buy_label(env: dict, rate_id: str, label_format: str) -> dict:
    """Purchase one label. Caller must already have passed decide()."""
    shippo = env.get("SHIPPO_API_KEY", "")
    easypost = env.get("EASYPOST_API_KEY", "")
    if not shippo and not easypost:
        return {"ok": False, "message": "No Shippo or EasyPost key is set. No label was bought."}
    if shippo:
        import json as _json
        import urllib.request
        req = urllib.request.Request(
            "https://api.goshippo.com/transactions",
            data=_json.dumps({"rate": rate_id, "label_file_type": label_format, "async": False}).encode(),
            headers={"Authorization": f"ShippoToken {shippo}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                body = _json.loads(response.read().decode())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": f"Shippo did not sell a label. {exc}"}
        if body.get("status") != "SUCCESS":
            return {"ok": False, "message": "Shippo did not return a successful label."}
        return {"ok": True, "message": "Label purchased.", "label_url": body.get("label_url") or "", "tracking": body.get("tracking_number") or ""}
    import json as _json
    import urllib.request
    token = base64_basic(easypost)
    req = urllib.request.Request(
        "https://api.easypost.com/v2/shipments",
        data=_json.dumps({"shipment": {"id": rate_id}}).encode(),
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
    )
    return {"ok": False, "message": "EasyPost buy needs the shipment id from a rate quote. No label was bought on an incomplete quote."}


def base64_basic(api_key: str) -> str:
    import base64
    return base64.b64encode(f"{api_key}:".encode()).decode()


def fulfill_after_purchase(shipment: dict, settings: dict, label: dict) -> dict:
    """Save the label, packing slip, and an unsent email. Print only on Windows."""
    import sys
    order = str(shipment.get("order_id") or "order").replace("/", "-")
    folder = DATA / "labels"
    folder.mkdir(parents=True, exist_ok=True)
    label_format = str(settings.get("label_format") or "PDF")
    suffix = "zpl" if label_format.upper() == "ZPL" else "pdf"
    label_path = folder / f"{order}-label.{suffix}"
    body = label.get("label_bytes")
    if isinstance(body, (bytes, bytearray)) and body:
        label_path.write_bytes(body)
    elif label.get("label_url"):
        import urllib.request
        try:
            with urllib.request.urlopen(label["label_url"], timeout=45) as response:
                label_path.write_bytes(response.read())
        except OSError as exc:
            label_path.write_text(f"Label URL was not downloaded: {exc}\n{label.get('label_url')}\n", encoding="utf-8")
    slip_path = folder / f"{order}-packing-slip.html"
    slip_path.write_text(packing_slip_html(shipment, settings), encoding="utf-8")
    drafts = ROOT / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    email_path = drafts / f"tracking-{order}.txt"
    email_path.write_text(
        tracking_email_draft(shipment, str(label.get("tracking") or ""), str(label.get("carrier") or "USPS")),
        encoding="utf-8",
    )
    printed = _print_saved(settings, label_path, slip_path, label_format)
    return {
        "label_file": str(label_path),
        "slip_file": str(slip_path),
        "email_draft": str(email_path),
        "printed": printed,
        "note": "The customer email is a draft. It was not sent.",
    }


def _print_saved(settings: dict, label_path: Path, slip_path: Path, label_format: str) -> str:
    import sys
    if sys.platform != "win32":
        return "Files saved. Printing runs on the Windows PC named in shipping settings."
    script = ROOT / "scripts" / "print-label.ps1"
    notes = []
    for path, printer, fmt in (
        (label_path, settings.get("label_printer") or "", label_format),
        (slip_path, settings.get("slip_printer") or "", "PDF"),
    ):
        if not printer:
            notes.append(f"No printer name set for {path.name}.")
            continue
        completed = __import__("subprocess").run(
            ["powershell", "-NoProfile", "-File", str(script), "-Path", str(path), "-PrinterName", str(printer), "-Format", "ZPL" if fmt.upper() == "ZPL" else "PDF"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        notes.append("Printed." if completed.returncode == 0 else (completed.stderr or "Print failed.")[-200:])
    return " ".join(notes)


def tracking_email_draft(shipment: dict, tracking: str, carrier: str) -> str:
    return (
        f"DRAFT — not sent\n"
        f"To: {shipment.get('to_name','')}\n"
        f"Subject: Your Earn It Not Given order {shipment.get('order_id')} has shipped\n\n"
        f"Your order is on the way with {carrier}. Tracking: {tracking}\n"
    )


def packing_slip_html(shipment: dict, settings: dict) -> str:
    items = "".join(
        f"<tr><td>{item['title']}</td><td>{item['qty']}</td><td>{item['sku']}</td></tr>"
        for item in shipment.get("items") or []
    )
    personal = shipment.get("personal_note") or ""
    personal_html = f"<p class='note'>{personal}</p>" if personal else ""
    sample = "<p class='sample'>SAMPLE PACKING SLIP — not a real order</p>" if shipment.get("sample") else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Packing slip {shipment.get('order_id')}</title>
<style>
  body {{ font-family: Georgia, serif; background:#f6f1e6; color:#1a140c; margin:0; }}
  .page {{ width: 720px; margin: 24px auto; background:#fffaf2; border:1px solid #e0d2b4; padding: 36px 40px; }}
  .brand {{ display:flex; gap:16px; align-items:center; }}
  .mark {{ width:54px; height:54px; border:3px solid #c6a15a; border-radius:50%; display:grid; place-items:center; color:#8c6a2f; font-weight:700; }}
  h1 {{ font-size: 28px; margin: 0; letter-spacing: .04em; }}
  .meta {{ color:#5c5144; }}
  table {{ width:100%; border-collapse: collapse; margin-top: 18px; }}
  th, td {{ text-align:left; padding: 8px 6px; border-bottom: 1px solid #eadfca; }}
  .thanks {{ margin-top: 28px; font-size: 18px; line-height: 1.45; }}
  .note {{ background:#f8f1df; padding: 12px 14px; }}
  .sample {{ color:#8c3b12; font-weight:700; letter-spacing:.04em; }}
</style></head>
<body><article class="page">
  {sample}
  <div class="brand"><div class="mark">E</div><div><h1>EARN IT NOT GIVEN</h1><p class="meta">Palo Alto · Packing slip</p></div></div>
  <p><strong>Order {shipment.get('order_id')}</strong> · {shipment.get('source','')}</p>
  <p class="meta">{shipment.get('to_name','')}<br>{shipment.get('to_street','')}<br>{shipment.get('to_city','')} {shipment.get('to_state','')} {shipment.get('to_zip','')}</p>
  <table><thead><tr><th>Item</th><th>Qty</th><th>SKU</th></tr></thead><tbody>{items}</tbody></table>
  <p class="thanks">{settings.get('thank_you','')}</p>
  {personal_html}
  <p class="meta">{shipment.get('note') or ''}</p>
</article></body></html>"""
