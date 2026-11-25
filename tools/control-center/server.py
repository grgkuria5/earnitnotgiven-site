#!/usr/bin/env python3
"""EarnItNotGiven Control Center. Localhost only.

Talks to Ollama on this PC, drafts text for George to approve, and can read
Etsy orders. It does not publish, email, or mark anything shipped unless he
clicks that button. It does not change Ollama or ComfyUI.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import ipaddress
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
DRAFTS = ROOT / "drafts"
DATA = ROOT / "data"
HOST = "127.0.0.1"
PORT = 8765
PREFERRED = ("llama3.2", "qwen2.5:3b", "phi3", "gemma2:2b", "llama3.2:1b")

SAMPLE_ORDERS = [
    {
        "id": "SAMPLE-1001",
        "source": "Etsy sample",
        "status": "unshipped",
        "title": "SAMPLE Orbit tee",
        "buyer": "Sample Buyer",
        "total": 28.00,
        "created": "2026-11-24",
        "sample": True,
    },
    {
        "id": "SAMPLE-1002",
        "source": "Site sample",
        "status": "shipped",
        "title": "SAMPLE poster",
        "buyer": "Sample Buyer",
        "total": 18.00,
        "created": "2026-11-20",
        "sample": True,
    },
]


def load_env() -> dict[str, str]:
    env = {}
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    for key in (
        "OLLAMA_HOST",
        "OLLAMA_MODEL",
        "ETSY_KEYSTRING",
        "ETSY_SHARED_SECRET",
        "ETSY_SHOP_ID",
        "ETSY_REDIRECT_URI",
        "PRINTIFY_TOKEN",
        "GITHUB_TOKEN",
        "GITHUB_REPO",
        "SHIPPO_API_KEY",
        "EASYPOST_API_KEY",
        "SHIPSTATION_API_KEY",
        "SHIPSTATION_API_SECRET",
        "STRIPE_SECRET_KEY",
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
    ):
        if os.environ.get(key):
            env[key] = os.environ[key]
    env.setdefault("OLLAMA_HOST", "http://127.0.0.1:11434")
    env.setdefault("ETSY_REDIRECT_URI", f"http://{HOST}:{PORT}/callback")
    env.setdefault("GITHUB_REPO", "grgkuria5/earnitnotgiven-site")
    return env


def host_allowed(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    name = (parsed.hostname or "").lower().strip("[]")
    if name in {"localhost", "127.0.0.1", "::1"} or name.endswith(".ts.net"):
        return True
    try:
        ip = ipaddress.ip_address(name)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip in ipaddress.ip_network("100.64.0.0/10")


def ollama_host(env: dict[str, str]) -> str:
    host = env.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    if not host_allowed(host):
        raise RuntimeError("Refusing a public Ollama address. Use localhost or a Tailscale address.")
    return host


def http_json(url: str, payload: dict | None = None, headers: dict | None = None, method: str | None = None, timeout: int = 30):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method or ("POST" if payload is not None else "GET"))
    req.add_header("accept", "application/json")
    if payload is not None:
        req.add_header("content-type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else {}


def list_models(env: dict[str, str]) -> list[str]:
    body = http_json(f"{ollama_host(env)}/api/tags", timeout=4)
    names = [row.get("name", "") for row in body.get("models", []) if row.get("name")]
    return names


def pick_model(env: dict[str, str], names: list[str]) -> str:
    wanted = env.get("OLLAMA_MODEL") or ""
    if wanted and wanted in names:
        return wanted
    for name in PREFERRED:
        if name in names:
            return name
    return names[0] if names else ""


def generate(env: dict[str, str], model: str, prompt: str) -> str:
    body = http_json(
        f"{ollama_host(env)}/api/generate",
        {"model": model, "prompt": prompt, "stream": False},
        timeout=180,
    )
    return str(body.get("response") or "").strip()


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def pkce_pair() -> tuple[str, str]:
    verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def redirect_ok(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "http" and (parsed.hostname or "") in {"127.0.0.1", "localhost"}


def etsy_key(env: dict[str, str]) -> str:
    key = env.get("ETSY_KEYSTRING", "")
    secret = env.get("ETSY_SHARED_SECRET", "")
    if key and secret:
        return f"{key}:{secret}"
    return key


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def low_stock() -> list[dict]:
    found = []
    folder = REPO / "src" / "content" / "products"
    if not folder.is_dir():
        return found
    for path in folder.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"^sample:\s*true", text, re.M):
            continue
        qty = re.search(r"^quantity:\s*(\d+)", text, re.M)
        title = re.search(r'^title:\s*"?(.*?)"?\s*$', text, re.M)
        amount = int(qty.group(1)) if qty else 0
        if amount <= 1:
            found.append({"file": path.name, "title": title.group(1) if title else path.stem, "quantity": amount})
    return found


def parse_money_csv(text: str) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return []
    keys = {key.lower(): key for key in rows[0].keys()}
    orders = []
    for row in rows:
        def cell(*names: str) -> str:
            for name in names:
                if name in keys and row.get(keys[name]):
                    return str(row[keys[name]]).strip()
            return ""

        title = cell("description", "item title", "name", "title") or "Imported order"
        total = cell("amount", "gross", "total")
        total = total.replace("$", "").replace(",", "")
        try:
            amount = float(total or "0")
        except ValueError:
            amount = 0.0
        orders.append(
            {
                "id": cell("id", "transaction id", "balance transaction") or f"LOCAL-{secrets.token_hex(3)}",
                "source": "import",
                "status": cell("status", "type") or "imported",
                "title": title,
                "buyer": cell("name", "from email address", "customer email") or "",
                "total": amount,
                "created": cell("created", "date", "created (utc)")[:10],
                "sample": False,
            }
        )
    return orders


def save_draft(kind: str, title: str, body: str, extra: dict | None = None) -> dict:
    DRAFTS.mkdir(parents=True, exist_ok=True)
    draft = {
        "id": secrets.token_hex(6),
        "kind": kind,
        "title": title,
        "body": body,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "draft",
        "extra": extra or {},
    }
    write_json(DRAFTS / f"{draft['id']}.json", draft)
    return draft


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text[:70] or "draft"


def approve_draft(draft: dict, env: dict[str, str], commit: bool) -> str:
    if draft.get("sample"):
        return "Sample drafts are not saved and are not committed."
    kind = draft.get("kind")
    if kind == "listing":
        target = REPO / "src" / "content" / "products" / f"{slugify(draft['title'])}.md"
        extra = draft.get("extra") or {}
        price = extra.get("price") or "0"
        category = extra.get("category") or "electronics"
        target.write_text(
            "\n".join(
                [
                    "---",
                    f'title: "{draft["title"].replace(chr(34), "")}"',
                    f"category: {category}",
                    'condition: "Used - Good"',
                    f"price: {price}",
                    "quantity: 1",
                    "draft: true",
                    "sample: false",
                    "---",
                    "",
                    draft.get("body") or "",
                    "",
                    "Suggested prices in this draft are suggestions, not a price you have to use.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        rel = target.relative_to(REPO).as_posix()
    elif kind == "guide":
        target = REPO / "src" / "content" / "guides" / f"{slugify(draft['title'])}.md"
        target.write_text(
            "\n".join(
                [
                    "---",
                    f'title: "{draft["title"].replace(chr(34), "")}"',
                    'description: "Draft from the Control Center. Not published."',
                    f'date: "{datetime.now().date().isoformat()}"',
                    "draft: true",
                    "---",
                    "",
                    draft.get("body") or "",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        rel = target.relative_to(REPO).as_posix()
    else:
        folder = ROOT / "approved"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{draft['id']}.md"
        target.write_text(f"# {draft['title']}\n\n{draft.get('body') or ''}\n", encoding="utf-8")
        rel = str(target)
        commit = False
    draft["status"] = "approved"
    write_json(DRAFTS / f"{draft['id']}.json", draft)
    if not commit:
        return f"Approved locally: {rel}. Nothing was pushed."
    token = env.get("GITHUB_TOKEN", "")
    if not token:
        return f"Approved locally: {rel}. No GitHub token is set, so nothing was pushed."
    import subprocess

    repo = env.get("GITHUB_REPO", "grgkuria5/earnitnotgiven-site")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return "Refusing the GitHub repo name in .env."
    subprocess.run(["git", "add", "--", rel], cwd=REPO, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add approved draft: {draft['title'][:60]}"],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    remote = f"https://x-access-token:{token}@github.com/{repo}.git"
    result = subprocess.run(["git", "push", remote, "HEAD:main"], cwd=REPO, capture_output=True, text=True)
    safe_err = (result.stderr or "").replace(token, "***")
    if result.returncode != 0:
        return f"Saved {rel} but the push failed: {safe_err[-400:]}"
    return f"Approved and pushed {rel}. The file is still a draft on the site until you turn draft off."


SAMPLE_DRAFTS = [
    {
        "id": "SAMPLE-LISTING",
        "kind": "listing",
        "title": "SAMPLE listing draft",
        "body": "SAMPLE. A title, a short description, and a suggested price range of $40–$60. Not a real listing.",
        "status": "draft",
        "sample": True,
    },
    {
        "id": "SAMPLE-PROMO",
        "kind": "promo",
        "title": "SAMPLE social post",
        "body": "SAMPLE. A caption you could post yourself. This app will not post it.",
        "status": "draft",
        "sample": True,
    },
]


PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>EarnItNotGiven Control Center</title>
  <style>
    :root { color-scheme: dark; --bg:#090c11; --card:#171e29; --text:#f4f7fb; --muted:#c5ceda; --gold:#e6c27a; --line:rgba(244,247,251,.14); }
    * { box-sizing: border-box; }
    body { margin:0; font-family: "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }
    header, main { width: min(1100px, calc(100% - 1.5rem)); margin: 0 auto; }
    header { padding: 1.2rem 0; }
    h1 { font-size: 1.8rem; margin: 0 0 .3rem; }
    .banner, .card, textarea, input, select { background: var(--card); border: 1px solid var(--line); border-radius: 14px; }
    .banner { padding: .8rem 1rem; color: var(--gold); }
    nav { display:flex; flex-wrap:wrap; gap:.4rem; margin: 1rem 0; }
    button, .link { min-height: 40px; border-radius: 999px; border: 0; padding: .45rem .9rem; font: inherit; cursor: pointer; }
    button.gold { background: var(--gold); color: #161008; font-weight: 700; }
    button.ghost, .link { background: transparent; color: var(--text); border: 1px solid var(--line); text-decoration: none; display:inline-flex; align-items:center; }
    textarea, input, select { width: 100%; color: var(--text); padding: .6rem .7rem; margin: .3rem 0 .7rem; }
    .grid { display:grid; gap: .8rem; }
    .card { padding: .9rem 1rem; }
    .muted { color: var(--muted); }
    table { width:100%; border-collapse: collapse; }
    td, th { text-align:left; padding:.4rem; border-bottom: 1px solid var(--line); vertical-align: top; }
    .sample { outline: 1px dashed var(--gold); }
  </style>
</head>
<body>
  <header>
    <h1>EarnItNotGiven Control Center</h1>
    <p class="muted">Local only. Drafts wait for your click. Nothing is emailed, posted, or shipped by itself.</p>
    <p id="status" class="banner">Checking Ollama…</p>
  </header>
  <main>
    <nav>
      <button class="ghost" type="button" data-tab="listings">Listings</button>
      <button class="ghost" type="button" data-tab="promos">Promos</button>
      <button class="ghost" type="button" data-tab="replies">Replies</button>
      <button class="ghost" type="button" data-tab="guides">Guides</button>
      <button class="ghost" type="button" data-tab="ship">Ship</button>
      <button class="ghost" type="button" data-tab="sync">Sync ideas</button>
      <button class="ghost" type="button" data-tab="sales">Sales</button>
      <button class="ghost" type="button" data-tab="labels">Shipping Station</button>
      <button class="ghost" type="button" data-tab="spec">Spec Checker</button>
    </nav>
    <section id="panel" class="grid"></section>
  </main>
  <script>
    const sampleDrafts = %%SAMPLE%%;
    const sampleOrders = %%ORDERS%%;
    const specProviders = %%SPEC%%;
    const tabs = {
      listings: `<form data-tool="listing" class="card"><h2>Bulk listing drafts</h2><p class="muted">Paste notes, one product per line. Suggested prices are suggestions.</p><textarea name="notes" rows="6">SAMPLE used laptop, 16 GB RAM, battery lasts a school day</textarea><button class="gold" type="submit">Draft listings</button></form>`,
      promos: `<form data-tool="promo" class="card"><h2>Promo and flash-deal drafts</h2><p class="muted">A social caption and a weekly flash-deal idea. You still post them yourself.</p><button class="gold" type="submit">Draft this week</button></form>`,
      replies: `<form data-tool="reply" class="card"><h2>Reply drafts</h2><textarea name="message" rows="6" placeholder="Paste an email or a trade-in note"></textarea><button class="gold" type="submit">Draft a reply</button><p class="muted">Nothing is sent.</p></form>`,
      guides: `<form data-tool="guide" class="card"><h2>Guide draft</h2><input name="topic" placeholder="Topic" /><button class="gold" type="submit">Draft a guide</button></form>`,
      ship: `<div class="card"><h2>Ship checklist and low stock</h2><div id="stock"></div><form data-tool="checklist"><button class="gold" type="submit">Draft the checklist</button></form></div>`,
      sync: `<form data-tool="sync" class="card"><h2>Description sync suggestions</h2><textarea name="notes" rows="5" placeholder="Paste an Etsy description and the site description"></textarea><button class="gold" type="submit">Draft suggestions</button></form>`,
      spec: `<div class="card"><h2>Spec Checker</h2><p class="muted">Opens the maker’s own page. It does not scrape it. WMI, OCR, and the iPhone copy run on this PC only.</p><label>Lookup<select id="spec-provider">${specProviders.map(p => `<option value="${p.id}">${p.group}: ${p.label}</option>`).join("")}</select></label><label>Tag, serial, model, IMEI, UPC, or photo path<input id="spec-id" value="SAMPLE7X" /></label><p><button class="gold" type="button" id="spec-go">Open official page</button> <button class="ghost" type="button" id="spec-wmi">Read this PC (WMI)</button> <button class="ghost" type="button" id="spec-ocr">Read a label photo</button> <button class="ghost" type="button" id="spec-phone">Import iPhone photos</button> <button class="ghost" type="button" id="spec-upc">Look up UPC</button></p><pre id="spec-out" class="muted">SAMPLE suggestion for Dell: category computers / laptops. Support URL is Dell’s service-tag page.</pre></div>`,
      labels: `<div class="card sample"><h2>Shipping Station</h2><p class="banner">SAMPLE DATA. Buy label will not purchase anything.</p><p>Order SAMPLE-1001 · Sample Buyer · Palo Alto, CA · customer paid shipping</p><p>Parcel preset: 8 oz, 10 x 8 x 1 in</p><table><tr><th>Carrier</th><th>Service</th><th>Rate</th></tr><tr><td>USPS</td><td>Ground Advantage</td><td>$6.40</td></tr><tr><td>UPS</td><td>Ground</td><td>$9.15</td></tr></table><p><a class="link" href="/packing-slip/sample" target="_blank">Open sample packing slip</a></p><form id="buy-form"><input type="hidden" name="rate_id" value="SAMPLE-USPS" /><button class="gold" type="submit">Buy label</button></form><p id="buy-note" class="muted">One click buys a real label only when a carrier key is set and the rate is under your caps. Auto-buy is off.</p></div>`,
      sales: `<div class="card sample"><h2>Sales</h2><p class="banner">SAMPLE DATA — not your shop. Connect Etsy to replace it.</p><p><a class="link" href="/auth/start">Connect Etsy</a> <a class="link" href="/export.csv">Export CSV</a></p><table><thead><tr><th>Order</th><th>Status</th><th>Total</th></tr></thead><tbody>${sampleOrders.map(row => `<tr><td>${row.id}<br>${row.title}</td><td>${row.status}</td><td>$${row.total.toFixed(2)}</td></tr>`).join("")}</tbody></table><form id="ship-form"><h3>Mark shipped</h3><input name="receipt_id" value="SAMPLE-1001" /><input name="carrier" value="usps" /><input name="tracking" placeholder="Tracking number" /><label><input type="checkbox" name="confirm" value="yes" /> I mean to send this to Etsy</label><button class="gold" type="submit">Submit tracking</button><p id="ship-note" class="muted"></p></form><form id="manual"><h3>Log a site order</h3><input name="title" placeholder="Title" /><input name="total" placeholder="Total" /><button class="ghost" type="submit">Save locally</button></form></div>`
    };
    const panel = document.querySelector("#panel");
    function show(name) { panel.innerHTML = tabs[name]; bind(); if (name === "ship") loadStock(); }
    document.querySelectorAll("[data-tab]").forEach(btn => btn.addEventListener("click", () => show(btn.dataset.tab)));
    function bind() {
      panel.querySelectorAll("form[data-tool]").forEach(form => form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(form).entries());
        data.tool = form.dataset.tool;
        const res = await fetch("/api/run", {method:"POST", headers:{"content-type":"application/json"}, body: JSON.stringify(data)});
        const body = await res.json();
        const note = document.createElement("p");
        note.textContent = body.message || body.error || "Saved a draft.";
        form.append(note);
      }));
      async function specCall(url, extra) {
        const identifier = document.querySelector("#spec-id").value;
        const res = await fetch(url, {method:"POST", headers:{"content-type":"application/json"}, body: JSON.stringify({provider: document.querySelector("#spec-provider").value, identifier, ...extra})});
        const body = await res.json();
        document.querySelector("#spec-out").textContent = JSON.stringify(body, null, 2);
        if (body.links && body.links[0]) window.open(body.links[0].url, "_blank", "noopener");
      }
      const specGo = document.querySelector("#spec-go");
      if (specGo) specGo.addEventListener("click", () => specCall("/api/spec/lookup", {}));
      const specWmi = document.querySelector("#spec-wmi");
      if (specWmi) specWmi.addEventListener("click", () => specCall("/api/spec/wmi", {}));
      const specOcr = document.querySelector("#spec-ocr");
      if (specOcr) specOcr.addEventListener("click", () => specCall("/api/spec/ocr", {path: document.querySelector("#spec-id").value}));
      const specPhone = document.querySelector("#spec-phone");
      if (specPhone) specPhone.addEventListener("click", () => specCall("/api/spec/iphone", {tag: document.querySelector("#spec-id").value}));
      const specUpc = document.querySelector("#spec-upc");
      if (specUpc) specUpc.addEventListener("click", () => specCall("/api/spec/upc", {code: document.querySelector("#spec-id").value}));
      const buy = document.querySelector("#buy-form");
      if (buy) buy.addEventListener("submit", async (event) => {
        event.preventDefault();
        const res = await fetch("/api/shipping/buy", {method:"POST", headers:{"content-type":"application/json"}, body: JSON.stringify({rate_id:"SAMPLE-USPS", amount:6.4, sample:true, auto:false, customer_paid_shipping:true})});
        const body = await res.json();
        document.querySelector("#buy-note").textContent = body.message || body.error;
      });
      const ship = document.querySelector("#ship-form");
      if (ship) ship.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(ship).entries());
        const res = await fetch("/api/ship", {method:"POST", headers:{"content-type":"application/json"}, body: JSON.stringify(data)});
        const body = await res.json();
        document.querySelector("#ship-note").textContent = body.message || body.error;
      });
    }
    async function loadStock() {
      const res = await fetch("/api/stock");
      const body = await res.json();
      document.querySelector("#stock").textContent = body.items.length ? body.items.map(row => `${row.title}: ${row.quantity} left`).join(" · ") : "No low-stock files, or only samples.";
    }
    fetch("/api/status").then(r => r.json()).then(body => {
      document.querySelector("#status").textContent = body.ollama ? `Ollama is up. Model: ${body.model}` : `Ollama is offline (${body.error}). Sample drafts are on screen. Nothing was invented as a real listing.`;
    });
    show("listings");
    const box = document.createElement("section");
    box.className = "card sample";
    box.innerHTML = `<h2>Sample drafts</h2><p class="muted">These are examples. Approve does not save them.</p>` + sampleDrafts.map(row => `<article><strong>${row.title}</strong><p>${row.body}</p><button class="ghost" type="button" data-approve="${row.id}">Approve sample</button></article>`).join("");
    document.querySelector("main").append(box);
    box.addEventListener("click", async (event) => {
      const id = event.target?.dataset?.approve;
      if (!id) return;
      const res = await fetch("/api/approve", {method:"POST", headers:{"content-type":"application/json"}, body: JSON.stringify({id, commit:false})});
      const body = await res.json();
      event.target.insertAdjacentHTML("afterend", `<p>${body.message}</p>`);
    });
  </script>
</body>
</html>"""


class App:
    def __init__(self):
        self.env = load_env()
        self.oauth: dict[str, str] = {}

    def status(self) -> dict:
        try:
            names = list_models(self.env)
            model = pick_model(self.env, names)
            return {"ollama": True, "models": names, "model": model, "error": ""}
        except Exception as exc:  # noqa: BLE001 — show a short offline message
            return {"ollama": False, "models": [], "model": "", "error": str(exc)}

    def run_tool(self, payload: dict) -> dict:
        status = self.status()
        if not status["ollama"]:
            return {"error": f"Ollama is offline. {status['error']} No draft was invented."}
        tool = payload.get("tool")
        model = status["model"]
        prompts = {
            "listing": "Write JSON with title, description, tags (list), seo_title, suggested_price_low, suggested_price_high. Mark prices as suggestions. Notes:\n" + str(payload.get("notes") or ""),
            "promo": "Write a short social caption for a Palo Alto tech shop and one flash-deal suggestion for slow stock. Do not claim it is posted. Stock notes:\n" + json.dumps(low_stock()),
            "reply": "Draft a polite reply the shop owner can send himself. Do not say it was sent. Message:\n" + str(payload.get("message") or ""),
            "guide": "Draft a buying guide outline and three paragraphs. Topic:\n" + str(payload.get("topic") or "used phones"),
            "checklist": "Write an order-to-ship checklist and mention low stock. Data:\n" + json.dumps(low_stock()),
            "sync": "Suggest edits so an Etsy description and a website description match, without publishing. Notes:\n" + str(payload.get("notes") or ""),
        }
        if tool not in prompts:
            return {"error": "Unknown tool."}
        text = generate(self.env, model, prompts[tool])
        draft = save_draft(tool if tool != "listing" else "listing", f"{tool} draft", text)
        return {"message": f"Draft {draft['id']} is waiting. Nothing was published.", "id": draft["id"]}

    def ship(self, payload: dict) -> dict:
        receipt = str(payload.get("receipt_id") or "")
        if receipt.startswith("SAMPLE") or payload.get("confirm") != "yes":
            return {"message": "Not sent. Sample orders are never submitted, and a real shipment needs the confirm box."}
        token = read_json(ROOT / ".tokens.json", {}).get("access_token", "")
        shop = self.env.get("ETSY_SHOP_ID", "")
        if not token or not shop:
            return {"error": "Connect Etsy and set ETSY_SHOP_ID before shipping."}
        tracking = str(payload.get("tracking") or "").strip()
        carrier = str(payload.get("carrier") or "usps").strip()
        if not tracking:
            return {"error": "Tracking number is required."}
        form = urllib.parse.urlencode({"tracking_code": tracking, "carrier_name": carrier, "send_bcc": "false"}).encode()
        req = urllib.request.Request(
            f"https://api.etsy.com/v3/application/shops/{urllib.parse.quote(shop)}/receipts/{urllib.parse.quote(receipt)}/tracking",
            data=form,
            method="POST",
        )
        req.add_header("content-type", "application/x-www-form-urlencoded")
        req.add_header("x-api-key", etsy_key(self.env))
        req.add_header("authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()[:300]
            return {"error": f"Etsy refused the shipment ({exc.code}). {detail}"}
        return {"message": f"Etsy accepted tracking for {receipt}."}


APP = App()


class Handler(BaseHTTPRequestHandler):
    def _host_ok(self) -> bool:
        host = (self.headers.get("host") or "").split(":")[0]
        return host in {"127.0.0.1", "localhost"}

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload).encode(), "application/json; charset=utf-8")

    def do_GET(self):  # noqa: N802
        if not self._host_ok():
            self._json(403, {"error": "localhost only"})
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            from spec_checker import providers
            page = PAGE.replace("%%SAMPLE%%", json.dumps(SAMPLE_DRAFTS)).replace("%%ORDERS%%", json.dumps(SAMPLE_ORDERS)).replace("%%SPEC%%", json.dumps(providers()))
            self._send(200, page.encode(), "text/html; charset=utf-8")
            return
        if path == "/api/status":
            self._json(200, APP.status())
            return
        if path == "/api/stock":
            self._json(200, {"items": low_stock()})
            return
        if path in {"/packing-slip", "/packing-slip/sample"}:
            from shipping_station import SAMPLE_SHIPMENT, load_settings, packing_slip_html
            shipment = dict(SAMPLE_SHIPMENT)
            shipment["personal_note"] = "SAMPLE note: hope the tee earns its place in the rotation."
            self._send(200, packing_slip_html(shipment, load_settings()).encode(), "text/html; charset=utf-8")
            return
        if path == "/export.csv":
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=["id", "source", "status", "title", "buyer", "total", "created", "sample"])
            writer.writeheader()
            writer.writerows(SAMPLE_ORDERS)
            extra = read_json(DATA / "site-orders.json", [])
            if isinstance(extra, list):
                writer.writerows(extra)
            self._send(200, buf.getvalue().encode(), "text/csv; charset=utf-8")
            return
        if path == "/auth/start":
            if not APP.env.get("ETSY_KEYSTRING"):
                self._json(400, {"error": "Set ETSY_KEYSTRING in .env first."})
                return
            if not redirect_ok(APP.env.get("ETSY_REDIRECT_URI", "")):
                self._json(400, {"error": "Redirect URI must be localhost."})
                return
            verifier, challenge = pkce_pair()
            state = secrets.token_urlsafe(16)
            APP.oauth = {"verifier": verifier, "state": state}
            query = urllib.parse.urlencode(
                {
                    "response_type": "code",
                    "client_id": APP.env["ETSY_KEYSTRING"],
                    "redirect_uri": APP.env["ETSY_REDIRECT_URI"],
                    "scope": "transactions_r transactions_w shops_r",
                    "state": state,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                }
            )
            self.send_response(302)
            self.send_header("location", f"https://www.etsy.com/oauth/connect?{query}")
            self.end_headers()
            return
        if path == "/callback":
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if query.get("state", [""])[0] != APP.oauth.get("state"):
                self._json(400, {"error": "OAuth state did not match."})
                return
            form = urllib.parse.urlencode(
                {
                    "grant_type": "authorization_code",
                    "client_id": APP.env.get("ETSY_KEYSTRING", ""),
                    "redirect_uri": APP.env.get("ETSY_REDIRECT_URI", ""),
                    "code": query.get("code", [""])[0],
                    "code_verifier": APP.oauth.get("verifier", ""),
                }
            ).encode()
            req = urllib.request.Request("https://api.etsy.com/v3/public/oauth/token", data=form)
            req.add_header("content-type", "application/x-www-form-urlencoded")
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    token = json.loads(response.read().decode())
            except urllib.error.HTTPError as exc:
                self._json(exc.code, {"error": "Etsy token exchange failed."})
                return
            write_json(ROOT / ".tokens.json", {"access_token": token.get("access_token", ""), "refresh_token": token.get("refresh_token", "")})
            self.send_response(302)
            self.send_header("location", "/")
            self.end_headers()
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if not self._host_ok():
            self._json(403, {"error": "localhost only"})
            return
        length = int(self.headers.get("content-length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "bad json"})
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/run":
            result = APP.run_tool(payload)
            self._json(200 if "message" in result else 503, result)
            return
        if path == "/api/approve":
            draft_id = str(payload.get("id") or "")
            sample = next((row for row in SAMPLE_DRAFTS if row["id"] == draft_id), None)
            if sample:
                self._json(200, {"message": approve_draft(sample, APP.env, False)})
                return
            path_json = DRAFTS / f"{draft_id}.json"
            if not path_json.is_file():
                self._json(404, {"error": "draft not found"})
                return
            draft = read_json(path_json, {})
            try:
                message = approve_draft(draft, APP.env, bool(payload.get("commit")))
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"error": str(exc)[:300]})
                return
            self._json(200, {"message": message})
            return
        if path == "/api/spec/lookup":
            from spec_checker import build_links, read_cache, suggest_category, write_cache
            provider = str(payload.get("provider") or "dell")
            identifier = str(payload.get("identifier") or "")
            try:
                links = build_links(provider, identifier)
            except (KeyError, ValueError) as exc:
                self._json(400, {"error": str(exc)})
                return
            suggestion = suggest_category(provider)
            record = {"identifier": identifier, "provider": provider, "links": links, "suggestion": suggestion, "sample": identifier.upper().startswith("SAMPLE")}
            if not record["sample"]:
                write_cache(DATA / "spec-cache", provider, identifier, record)
            else:
                cached = read_cache(DATA / "spec-cache", provider, identifier)
                record["cached"] = bool(cached)
            self._json(200, record)
            return
        if path == "/api/spec/wmi":
            from spec_checker import read_local_windows, suggest_category
            try:
                record = read_local_windows()
            except RuntimeError as exc:
                self._json(200, {"ok": False, "message": str(exc)})
                return
            record["suggestion"] = suggest_category("dell")
            self._json(200, record)
            return
        if path == "/api/spec/ocr":
            from spec_checker import ocr_label
            self._json(200, ocr_label(str(payload.get("path") or payload.get("identifier") or "")))
            return
        if path == "/api/spec/iphone":
            from spec_checker import import_iphone_photos
            self._json(200, import_iphone_photos(str(payload.get("tag") or payload.get("identifier") or "")))
            return
        if path == "/api/spec/upc":
            from spec_checker import lookup_upc, suggest_category
            code = str(payload.get("code") or payload.get("identifier") or "")
            if code.upper().startswith("SAMPLE"):
                self._json(200, {"ok": False, "message": "SAMPLE is not a barcode. No lookup was sent."})
                return
            found = lookup_upc(code, APP.env.get("UPCITEMDB_KEY", ""))
            found["suggestion"] = suggest_category("upc")
            self._json(200, found)
            return
        if path == "/api/shipping/buy":
            from shipping_station import append_log, buy_label, decide, fulfill_after_purchase, load_settings
            settings = load_settings()
            sample = bool(payload.get("sample")) or str(payload.get("rate_id") or "").startswith("SAMPLE")
            allowed, reason = decide(
                float(payload.get("amount") or 0),
                settings,
                auto=bool(payload.get("auto")),
                customer_paid_shipping=bool(payload.get("customer_paid_shipping")),
                sample=sample,
            )
            if not allowed:
                append_log({"action": "refused", "amount": payload.get("amount"), "reason": reason, "rate_id": payload.get("rate_id")})
                self._json(200, {"message": reason, "purchased": False})
                return
            result = buy_label(APP.env, str(payload.get("rate_id") or ""), str(settings.get("label_format") or "PDF"))
            if not result.get("ok"):
                append_log({"action": "refused", "amount": payload.get("amount"), "reason": result.get("message"), "rate_id": payload.get("rate_id")})
                self._json(200, {"message": result.get("message"), "purchased": False})
                return
            raw = payload.get("shipment") if isinstance(payload.get("shipment"), dict) else {}
            shipment = {
                "sample": False,
                "order_id": str(raw.get("order_id") or payload.get("order_id") or "order"),
                "source": str(raw.get("source") or payload.get("source") or ""),
                "to_name": str(raw.get("to_name") or payload.get("to_name") or ""),
                "to_street": str(raw.get("to_street") or ""),
                "to_city": str(raw.get("to_city") or ""),
                "to_state": str(raw.get("to_state") or ""),
                "to_zip": str(raw.get("to_zip") or ""),
                "items": raw.get("items") if isinstance(raw.get("items"), list) else [],
                "note": str(raw.get("note") or ""),
                "personal_note": str(raw.get("personal_note") or ""),
            }
            result["carrier"] = result.get("carrier") or str(payload.get("carrier") or "USPS")
            done = fulfill_after_purchase(shipment, settings, result)
            etsy_note = ""
            if "etsy" in shipment["source"].lower():
                if result.get("tracking"):
                    sent = APP.ship({
                        "receipt_id": shipment["order_id"],
                        "confirm": "yes",
                        "tracking": result.get("tracking"),
                        "carrier": str(payload.get("carrier") or "usps"),
                    })
                    etsy_note = sent.get("message") or sent.get("error") or ""
                else:
                    etsy_note = "Etsy was not updated because the label had no tracking number."
            append_log({"action": "purchased", "amount": payload.get("amount"), "reason": result.get("message"), "rate_id": payload.get("rate_id"), "email_draft": done.get("email_draft")})
            message = " ".join(part for part in (result.get("message"), done.get("printed"), done.get("note"), etsy_note) if part)
            self._json(200, {"message": message, "purchased": True, "email_draft": done.get("email_draft")})
            return
        if path == "/api/ship":
            self._json(200, APP.ship(payload))
            return
        if path == "/api/site-order":
            orders = read_json(DATA / "site-orders.json", [])
            if not isinstance(orders, list):
                orders = []
            orders.append(
                {
                    "id": f"LOCAL-{secrets.token_hex(3)}",
                    "source": "manual",
                    "status": "unshipped",
                    "title": str(payload.get("title") or "Site order"),
                    "buyer": str(payload.get("buyer") or ""),
                    "total": float(payload.get("total") or 0),
                    "created": datetime.now().date().isoformat(),
                    "sample": False,
                }
            )
            write_json(DATA / "site-orders.json", orders)
            self._json(200, {"message": "Saved on this PC. Nothing was sent."})
            return
        self._json(404, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s\n" % (fmt % args))


def run_daily() -> int:
    env = load_env()
    try:
        names = list_models(env)
        model = pick_model(env, names)
        text = generate(env, model, "Draft a one-paragraph shop promo and one flash-deal idea. Do not say it was posted. Low stock:\n" + json.dumps(low_stock()))
        save_draft("promo", "Daily promo draft", text)
        print("Daily draft saved. Nothing was published.")
    except Exception as exc:  # noqa: BLE001
        save_draft("error", "Ollama offline", f"No promo was written. {exc}")
        print(f"Ollama offline. {exc}")
    return 0


def self_check() -> int:
    assert host_allowed("http://127.0.0.1:11434")
    assert not host_allowed("https://example.com")
    assert not host_allowed("http://8.8.8.8")
    assert host_allowed("http://100.64.0.2:11434")
    assert redirect_ok("http://127.0.0.1:8765/callback")
    assert not redirect_ok("https://evil.example/callback")
    verifier, challenge = pkce_pair()
    assert len(challenge) >= 43 and verifier
    message = approve_draft(SAMPLE_DRAFTS[0], {}, False)
    assert "Sample" in message
    ship = App().ship({"receipt_id": "SAMPLE-1001", "confirm": "yes", "tracking": "123"})
    assert "Not sent" in ship["message"]
    from shipping_station import decide, DEFAULT_SETTINGS
    settings = dict(DEFAULT_SETTINGS)
    ok, why = decide(6.4, settings, auto=False, customer_paid_shipping=True, sample=True)
    assert not ok and "Sample" in why
    ok, why = decide(40, settings, auto=False, customer_paid_shipping=True, sample=False)
    assert not ok and "per-label" in why
    ok, why = decide(9, settings, auto=True, customer_paid_shipping=False, sample=False)
    assert not ok and "Auto-buy" in why
    ok, why = decide(9, settings, auto=False, customer_paid_shipping=True, sample=False)
    assert ok
    print("control center checks passed")
    return 0


def main() -> int:
    if "--self-check" in sys.argv:
        return self_check()
    if "--daily" in sys.argv:
        return run_daily()
    if not redirect_ok(load_env().get("ETSY_REDIRECT_URI", f"http://{HOST}:{PORT}/callback")):
        print("ETSY_REDIRECT_URI must stay on localhost.", file=sys.stderr)
        return 1
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Control Center at http://{HOST}:{PORT}  (this computer only)")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
