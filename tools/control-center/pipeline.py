"""Phone-to-listing pipeline. Drafts stay unpublished until George approves."""

from __future__ import annotations

import json
import re
import secrets
import statistics
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SELLER = "workhard1140"
NOTIFY_EMAIL = "gkuria175@gmail.com"
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}

SAMPLE_ITEM = {
    "id": "SAMPLE",
    "sku": "SAMPLE-SKU",
    "sample": True,
    "stage": "priced",
    "title": "SAMPLE Latitude laptop",
    "brand": "Dell",
    "model": "SAMPLE",
    "specs": "SAMPLE 16 GB RAM. Not read from a machine.",
    "comps": [42.0, 48.0, 51.0, 55.0],
    "median": 49.5,
    "suggested": 49.5,
    "comp_note": "SAMPLE DATA. No eBay call was made.",
    "sold_url": "https://www.ebay.com/sch/i.html?_nkw=SAMPLE+Latitude&LH_Sold=1&LH_Complete=1",
    "token": "sample",
    "photos": 1,
    "draft": {
        "title": "SAMPLE Dell Latitude, refreshed and tested",
        "description": "SAMPLE. Defects would be described, not hidden. This is not a real listing.",
        "condition": "Used - Good",
        "condition_notes": "SAMPLE. Say what was tested and what is worn.",
        "refreshed_tested": True,
        "price": 49.5,
        "shipping_preset": "1 lb, 12 x 9 x 3 in",
        "seller": SELLER,
        "promoted": False,
    },
}


def log_event(event: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    event = dict(event)
    event["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with (DATA / "pipeline-log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def products_root(env: dict) -> Path:
    raw = env.get("PRODUCTS_ROOT") or r"C:\Users\Hacking\EarnItNotGiven\Products"
    return Path(raw)


def inbox_dir(env: dict) -> Path:
    return products_root(env) / "_inbox"


def items_path() -> Path:
    return DATA / "pipeline-items.json"


def load_items() -> list[dict]:
    path = items_path()
    if not path.is_file():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return rows if isinstance(rows, list) else []


def save_items(rows: list[dict]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    items_path().write_text(json.dumps(rows, indent=2), encoding="utf-8")


def public_items() -> list[dict]:
    rows = [row for row in load_items() if not row.get("sample")]
    return [SAMPLE_ITEM, *rows]


def find_item(item_id: str) -> dict | None:
    if item_id == "SAMPLE":
        return dict(SAMPLE_ITEM)
    for row in load_items():
        if row.get("id") == item_id:
            return row
    return None


def new_sku() -> str:
    day = datetime.now().strftime("%Y%m%d")
    return f"EING-{day}-{secrets.token_hex(2).upper()}"


def median_price(prices: list[float]) -> float | None:
    clean = sorted(float(price) for price in prices if float(price) > 0)
    if not clean:
        return None
    return round(float(statistics.median(clean[:5])), 2)


def sold_search_url(query: str) -> str:
    return "https://www.ebay.com/sch/i.html?" + urllib.parse.urlencode(
        {"_nkw": query, "LH_Sold": "1", "LH_Complete": "1", "rt": "nc"}
    )


def suggested_price(prices: list[float]) -> float | None:
    return median_price(prices)


def vision_model(names: list[str]) -> str:
    for name in names:
        lowered = name.lower()
        if any(token in lowered for token in ("llava", "vision", "moondream", "minicpm")):
            return name
    return ""


def _convert_to_jpg(source: Path, dest: Path) -> str:
    try:
        import pillow_heif  # type: ignore

        pillow_heif.register_heif_opener()
    except Exception:
        pass
    try:
        from PIL import Image, ImageOps
    except ImportError:
        if source.suffix.lower() in {".heic", ".heif"}:
            return "HEIC was kept. Install Pillow and pillow-heif to make a JPG. Nothing was invented."
        dest.write_bytes(source.read_bytes())
        return "Saved the original. Pillow is not installed, so it was not converted."
    try:
        image = Image.open(source)
        image = ImageOps.exif_transpose(image)
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, "JPEG", quality=90)
        return "Saved as JPG."
    except Exception as exc:  # noqa: BLE001
        return f"Could not convert that photo. {exc}"


def store_photo(env: dict, sku: str, filename: str, blob: bytes) -> dict:
    folder = products_root(env) / sku / "photos"
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "", Path(filename).name) or "photo.jpg"
    raw_path = folder / f"raw-{safe}"
    raw_path.write_bytes(blob)
    jpg_path = folder / f"{raw_path.stem}.jpg"
    note = _convert_to_jpg(raw_path, jpg_path)
    return {"file": jpg_path.name, "note": note}


def cleanup_photo(path: Path) -> str:
    """Straighten from EXIF, trim a plain border, and resize. Do not hide wear."""
    try:
        from PIL import Image, ImageEnhance, ImageOps, ImageStat
    except ImportError:
        return "Pillow is not installed. The original photo was kept unchanged."
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    # Trim only a near-white margin. Leave the object, including scuffs, alone.
    gray = ImageOps.grayscale(image)
    mask = gray.point(lambda pixel: 255 if pixel < 245 else 0)
    bbox = mask.getbbox()
    if bbox:
        image = image.crop(bbox)
    stats = ImageStat.Stat(image)
    average = sum(stats.mean) / 3
    if 70 < average < 150:
        image = ImageEnhance.Brightness(image).enhance(1.05)
    image.thumbnail((1600, 1600))
    image.save(path, "JPEG", quality=88)
    return "Cropped a plain edge, kept the EXIF rotation, and resized. Wear was not removed."


def ebay_prices(env: dict, query: str) -> dict:
    """A public sold-listings link only. This shop has no eBay API key."""
    del env
    return {
        "prices": [],
        "source": "",
        "sold_url": sold_search_url(query),
        "note": "Open the sold-listings search and read the prices yourself. No price was invented, and no eBay API was called.",
    }


def notify_text(item: dict, base: str) -> str:
    comps = ", ".join(f"${price:.2f}" for price in item.get("comps") or []) or "none yet"
    median = item.get("median")
    suggested = item.get("suggested")
    lines = [
        f"{item.get('sku')} {item.get('title') or ''}",
        f"Sold comps: {comps}",
        f"Median: {'' if median is None else f'${median:.2f}'}",
        f"Suggested price: {'' if suggested is None else f'${suggested:.2f}'}",
        item.get("comp_note") or "",
        item.get("sold_url") or "",
        f"Looks good, continue: {base}/snap/continue/{item.get('id')}?token={item.get('token')}",
        f"Skip: {base}/snap/skip/{item.get('id')}?token={item.get('token')}",
    ]
    return "\n".join(line for line in lines if line)


def send_notify(env: dict, item: dict, base: str) -> str:
    text = notify_text(item, base)
    topic = env.get("NTFY_TOPIC", "")
    if topic and re.fullmatch(r"[A-Za-z0-9_-]{8,64}", topic):
        server = env.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
        import urllib.request

        continue_url = f"{base}/snap/continue/{item.get('id')}?token={item.get('token')}"
        skip_url = f"{base}/snap/skip/{item.get('id')}?token={item.get('token')}"
        req = urllib.request.Request(
            f"{server}/{topic}",
            data=text.encode(),
            headers={
                "title": f"Price check {item.get('sku')}",
                "actions": f"http, Looks good continue, {continue_url}; http, Skip, {skip_url}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                response.read()
            log_event({"action": "notify", "sku": item.get("sku"), "via": "ntfy"})
            return "Sent to your ntfy topic."
        except Exception as exc:  # noqa: BLE001
            log_event({"action": "notify-failed", "sku": item.get("sku"), "via": "ntfy", "error": str(exc)[:180]})
    hook = env.get("HA_NOTIFY_URL", "")
    if hook.startswith("https://") or hook.startswith("http://"):
        import urllib.request

        req = urllib.request.Request(hook, data=json.dumps({"message": text}).encode(), headers={"content-type": "application/json"})
        token = env.get("HA_TOKEN", "")
        if token:
            req.add_header("authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                response.read()
            log_event({"action": "notify", "sku": item.get("sku"), "via": "home-assistant"})
            return "Sent to Home Assistant."
        except Exception as exc:  # noqa: BLE001
            log_event({"action": "notify-failed", "sku": item.get("sku"), "via": "home-assistant", "error": str(exc)[:180]})
    drafts = ROOT / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    path = drafts / f"notify-{item.get('sku')}.txt"
    path.write_text(f"DRAFT — not sent\nTo: {NOTIFY_EMAIL}\nSubject: Price check {item.get('sku')}\n\n{text}\n", encoding="utf-8")
    log_event({"action": "notify-draft", "sku": item.get("sku"), "email": NOTIFY_EMAIL})
    return f"No ntfy topic or Home Assistant hook answered. An email draft for {NOTIFY_EMAIL} was saved and not sent."


def site_draft_markdown(item: dict) -> str:
    draft = item.get("draft") or {}
    title = str(draft.get("title") or item.get("title") or item.get("sku")).replace('"', "")
    price = draft.get("price") if draft.get("price") is not None else 0
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            "category: computers",
            'condition: "Used - Good"',
            f"price: {price}",
            "quantity: 1",
            "draft: true",
            "sample: false",
            "refreshed_tested: true",
            f"sku: {item.get('sku')}",
            "---",
            "",
            str(draft.get("description") or ""),
            "",
            str(draft.get("condition_notes") or ""),
            "",
            "Suggested price is a suggestion from sold comps. It is not a price you have to use.",
            f"eBay seller username stays {SELLER}. No Promoted Listings.",
            "",
        ]
    )


def token_matches(item: dict, token: str) -> bool:
    saved = str(item.get("token") or "")
    given = str(token or "")
    if not saved or not given or len(saved) != len(given):
        return False
    import hmac
    return hmac.compare_digest(saved, given)


def remember(item: dict) -> None:
    rows = [row for row in load_items() if row.get("id") != item.get("id")]
    rows.append(item)
    save_items(rows)


def start_item(env: dict, note: str, files: list[tuple[str, bytes]]) -> dict:
    saved = []
    sku = new_sku()
    for name, blob in files[:8]:
        if not blob or len(blob) > 12_000_000:
            continue
        suffix = Path(name).suffix.lower()
        if suffix not in IMAGE_TYPES:
            continue
        saved.append(store_photo(env, sku, name, blob))
    if not saved:
        return {"ok": False, "message": "No photo was saved. Use a JPG, PNG, or HEIC."}
    query = (note or sku).splitlines()[0][:120]
    priced = ebay_prices(env, query)
    prices = priced.get("prices") or []
    item = {
        "id": secrets.token_hex(4),
        "sku": sku,
        "sample": False,
        "stage": "priced",
        "title": query,
        "note": note[:500],
        "photos": len(saved),
        "photo_notes": [row.get("note") for row in saved],
        "token": secrets.token_urlsafe(18),
        "comps": prices,
        "median": median_price(prices),
        "suggested": suggested_price(prices),
        "sold_url": priced.get("sold_url"),
        "comp_note": priced.get("note"),
        "seller": SELLER,
        "identify_note": "Waiting to read the first photo.",
    }
    remember(item)
    log_event({"action": "upload", "sku": sku, "photos": len(saved)})
    return {"ok": True, "item": item}


def attach_identity(item: dict, identity: dict) -> dict:
    if identity.get("title"):
        item["title"] = str(identity["title"])[:140]
    item["brand"] = str(identity.get("brand") or "")[:80]
    item["model"] = str(identity.get("model") or "")[:80]
    item["specs"] = str(identity.get("specs") or "")[:500]
    item["identify_note"] = str(identity.get("note") or "")[:300]
    item["stage"] = "priced"
    if not item.get("sample"):
        remember(item)
    return item


def finish_draft(env: dict, item: dict, written: str) -> dict:
    folder = products_root(env) / str(item.get("sku")) / "photos"
    notes = []
    if folder.is_dir():
        for path in folder.glob("*.jpg"):
            notes.append(cleanup_photo(path))
    item["cleanup"] = notes or ["No JPG was cleaned."]
    text = written.strip() or (item.get("note") or "")
    if not text:
        text = "Description still needs George's words. Specs were not guessed."
    price = item.get("suggested") if item.get("suggested") is not None else 0
    item["draft"] = {
        "title": (item.get("title") or item.get("sku"))[:80],
        "description": text[:4000],
        "condition": "Used - Good",
        "condition_notes": "Refreshed and tested by the seller. Describe wear honestly. Do not hide defects.",
        "refreshed_tested": True,
        "price": price,
        "shipping_preset": "Confirm weight and box size before buying a label.",
        "seller": SELLER,
        "promoted": False,
    }
    item["stage"] = "drafted"
    paste_path = ROOT / "drafts" / f"ebay-{item.get('sku')}.txt"
    paste_path.parent.mkdir(parents=True, exist_ok=True)
    paste_path.write_text(ebay_paste(item), encoding="utf-8")
    item["ebay_paste"] = str(paste_path)
    slug = re.sub(r"[^a-z0-9]+", "-", str(item["draft"]["title"]).lower()).strip("-")[:70] or "draft"
    site_path = ROOT.parents[1] / "src" / "content" / "products" / f"{slug}.md"
    site_path.write_text(site_draft_markdown(item), encoding="utf-8")
    item["site_file"] = site_path.relative_to(ROOT.parents[1]).as_posix()
    remember(item)
    log_event({"action": "draft", "sku": item.get("sku"), "seller": SELLER, "promoted": False})
    return item


def publish_local(item: dict) -> str:
    """Turn the site file public only after Approve. Does not call eBay here."""
    rel = item.get("site_file") or ""
    path = ROOT.parents[1] / rel if rel else None
    if not path or not path.is_file():
        return "No site draft file was found."
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^draft:\s*true", "draft: false", text, count=1, flags=re.M)
    path.write_text(text, encoding="utf-8")
    item["stage"] = "approved"
    remember(item)
    log_event({"action": "approve-site", "sku": item.get("sku"), "file": rel})
    return f"Site draft is now public in {rel}. Commit it when you are ready."


def apply_action(item_id: str, token: str, action: str) -> dict:
    item = find_item(item_id)
    if not item or not token_matches(item, token):
        return {"ok": False, "message": "That link does not match a device on this PC."}
    if item.get("sample"):
        log_event({"action": action, "sku": item.get("sku"), "sample": True})
        return {"ok": False, "message": "Sample was not drafted, not published, and not sent to eBay."}
    if action == "skip":
        item["stage"] = "skipped"
        remember(item)
        log_event({"action": "skip", "sku": item.get("sku")})
        return {"ok": True, "message": "Skipped. Nothing was listed."}
    return {"ok": True, "message": "continue", "item": item}


def scan_inbox(env: dict) -> int:
    inbox = inbox_dir(env)
    if not inbox.is_dir():
        return 0
    files = [path for path in inbox.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_TYPES]
    if not files:
        return 0
    blobs = [(path.name, path.read_bytes()) for path in files[:8]]
    result = start_item(env, "Inbox drop", blobs)
    if not result.get("ok"):
        return 0
    for path in files[:8]:
        path.unlink(missing_ok=True)
    log_event({"action": "inbox", "sku": result["item"].get("sku")})
    return 1


def snap_page(base: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#14110c" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-title" content="Snap & List" />
  <link rel="manifest" href="/snap/manifest.webmanifest" />
  <title>Snap & List</title>
  <style>
    :root {{ color-scheme: dark; --bg:#100e0b; --card:#1b1814; --text:#f6f1e7; --gold:#e6c27a; --muted:#c8bba6; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    main {{ width: min(480px, 100%); margin: 0 auto; padding: 1.2rem 1rem 3rem; }}
    h1 {{ font-size: 1.7rem; margin: 0 0 .3rem; }}
    p {{ color: var(--muted); line-height: 1.4; }}
    form, .card {{ background: var(--card); border: 1px solid rgba(230,194,122,.35); border-radius: 18px; padding: 1rem; }}
    label {{ display:block; margin: .6rem 0 .2rem; }}
    input, textarea {{ width:100%; font: inherit; padding: .8rem; border-radius: 12px; border: 1px solid rgba(255,255,255,.15); background:#0c0a08; color: var(--text); }}
    input[type=file] {{ padding: .6rem; }}
    button {{ width:100%; margin-top: .8rem; min-height: 52px; border:0; border-radius: 999px; background: var(--gold); color:#1a140c; font: inherit; font-weight: 750; }}
    .mark {{ width:72px; height:72px; object-fit: contain; }}
  </style>
</head>
<body>
  <main>
    <h1>Snap & List</h1>
    <p>Take photos of one device. The first picture starts a price check. Nothing is published from this screen.</p>
    <form action="/snap/upload" method="post" enctype="multipart/form-data">
      <label for="photos">Camera or library</label>
      <input id="photos" name="photos" type="file" accept="image/*" capture="environment" multiple required />
      <label for="note">What you already know</label>
      <textarea id="note" name="note" rows="3" placeholder="Dell tag, cracks, battery, included charger"></textarea>
      <button type="submit">Send this device</button>
    </form>
    <p>Drops in the inbox folder on the desktop are picked up too. Add this page to your home screen from the browser menu.</p>
    <p>Open on this PC at {base}/snap</p>
  </main>
  <script>
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/snap/sw.js");
  </script>
</body>
</html>"""


def notice_page(item: dict) -> str:
    comps = "".join(f"<li>${price:.2f}</li>" for price in item.get("comps") or [])
    sample = "<p class='sample'>SAMPLE DATA. No alert was sent and no price was fetched.</p>" if item.get("sample") else ""
    median = item.get("median")
    suggested = item.get("suggested")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Price check {item.get('sku')}</title>
<style>
  body {{ margin:0; font-family: Georgia, serif; background:#14110c; color:#f6f1e7; }}
  main {{ width:min(440px,100%); margin:0 auto; padding:1.2rem; }}
  .card {{ background:#221e18; border-radius:18px; padding:1rem 1.1rem; }}
  .sample {{ color:#e6c27a; font-weight:700; }}
  button, a.btn {{ display:block; text-align:center; margin-top:.7rem; padding:.9rem; border-radius:999px; text-decoration:none; font-weight:700; }}
  .go {{ background:#e6c27a; color:#1a140c; }}
  .skip {{ background:transparent; color:#f6f1e7; border:1px solid rgba(255,255,255,.3); }}
</style></head>
<body><main><article class="card">
  {sample}
  <h1>Price check</h1>
  <p>{item.get('sku')} · {item.get('title') or ''}</p>
  <ul>{comps or '<li>No sold prices yet</li>'}</ul>
  <p>Median {'' if median is None else f'${median:.2f}'} · Suggested {'' if suggested is None else f'${suggested:.2f}'}</p>
  <p>{item.get('comp_note') or ''}</p>
  <p><a href="{item.get('sold_url') or '#'}">Sold listings on eBay</a></p>
  <a class="btn go" href="/snap/continue/{item.get('id')}?token={item.get('token')}">Looks good, continue</a>
  <a class="btn skip" href="/snap/skip/{item.get('id')}?token={item.get('token')}">Skip</a>
</article></main></body></html>"""


def preview_page(item: dict) -> str:
    draft = item.get("draft") or {}
    sample = "<p class='sample'>SAMPLE PREVIEW. Approve will not publish this.</p>" if item.get("sample") else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Approve {item.get('sku')}</title>
<style>
  body {{ margin:0; font-family: "Segoe UI", sans-serif; background:#100e0b; color:#f6f1e7; }}
  main {{ width:min(560px,100%); margin:0 auto; padding:1.2rem; }}
  .card {{ background:#1c1914; border:1px solid rgba(230,194,122,.4); border-radius:18px; padding:1rem; }}
  .sample {{ color:#e6c27a; }}
  button {{ min-height:48px; border:0; border-radius:999px; background:#e6c27a; color:#1a140c; font:inherit; font-weight:750; padding:0 1rem; }}
</style></head>
<body><main><article class="card">
  {sample}
  <p>Seller {SELLER} · unpublished draft · no Promoted Listings</p>
  <h1>{draft.get('title') or item.get('title')}</h1>
  <p>${draft.get('price')} · {draft.get('condition')} · Refreshed & tested by seller</p>
  <p>{draft.get('description') or ''}</p>
  <p>{draft.get('condition_notes') or ''}</p>
  <p>Shipping preset: {draft.get('shipping_preset') or ''}</p>
  <form method="post" action="/snap/approve/{item.get('id')}">
    <input type="hidden" name="token" value="{item.get('token')}" />
    <button type="submit">Approve and publish</button>
  </form>
</article></main></body></html>"""


def ebay_paste(item: dict) -> str:
    draft = item.get("draft") or {}
    return "\n".join(
        [
            f"eBay draft for seller {SELLER}",
            "Do not change this username.",
            "Do not turn on Promoted Listings or any paid upgrade.",
            "This file is a paste draft. It was not published.",
            "",
            f"Title: {draft.get('title') or ''}",
            f"Price: {draft.get('price')}",
            f"Condition: {draft.get('condition') or ''}",
            f"Shipping preset: {draft.get('shipping_preset') or ''}",
            "",
            str(draft.get("description") or ""),
            "",
            str(draft.get("condition_notes") or ""),
            "",
        ]
    )
