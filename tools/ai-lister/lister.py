#!/usr/bin/env python3
"""Draft product listings with a local Ollama model.

This talks only to loopback. It writes markdown under tools/ai-lister/review/
and never copies files into the live catalog.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REVIEW = HERE / "review"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    host = str(data.get("host") or "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(host)
    if parsed.scheme not in {"http"} or (parsed.hostname or "").lower() not in LOCAL_HOSTS:
        sys.exit(f"Refusing non-local Ollama host: {host}")
    if parsed.port not in {None, 11434} and "--allow-port" not in sys.argv:
        sys.exit("Refusing an unexpected local port. Pass --allow-port if you run Ollama elsewhere on this PC.")
    return {"host": host, "model": str(data.get("model") or "llama3.2")}


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text[:80] or "draft"


def ask_ollama(config: dict, notes: str, category: str, condition: str) -> dict:
    prompt = (
        "You write a product listing for a small Palo Alto resale shop. "
        "Return JSON only with keys title, description, specs, tags. "
        "specs is a list of {name, value}. tags is a list of short strings. "
        "Do not invent awards, star ratings, or health claims. "
        "If a fact is not in the notes, leave it out.\n"
        f"Category: {category}\nCondition: {condition}\nNotes: {notes}"
    )
    body = json.dumps({"model": config["model"], "prompt": prompt, "stream": False, "format": "json"}).encode()
    request = urllib.request.Request(
        f"{config['host']}/api/generate",
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.URLError as error:
        sys.exit(f"Ollama did not answer at {config['host']}. Start it with: ollama serve\n{error}")
    raw = payload.get("response") or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        sys.exit("Ollama did not return JSON. Nothing was written.")


def yaml_string(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_review(row: dict, listing: dict, price: str, quantity: str) -> Path:
    title = str(listing.get("title") or "Untitled draft").strip()
    REVIEW.mkdir(parents=True, exist_ok=True)
    target = REVIEW / f"{slugify(title)}.md"
    specs = listing.get("specs") if isinstance(listing.get("specs"), list) else []
    tags = listing.get("tags") if isinstance(listing.get("tags"), list) else []
    lines = [
        "---",
        f"title: {yaml_string(title)}",
        f"category: {yaml_string(row.get('category') or 'electronics')}",
        f"condition: {yaml_string(row.get('condition') or 'Used - Good')}",
        f"price: {price or '0'}",
        f"quantity: {quantity or '1'}",
        "draft: true",
        "sample: false",
        "review_status: unreviewed",
        "specs:",
    ]
    for spec in specs:
        if isinstance(spec, dict) and spec.get("name") and spec.get("value"):
            lines.append(f"  - name: {yaml_string(str(spec['name']))}")
            lines.append(f"    value: {yaml_string(str(spec['value']))}")
    if len(lines) == 10:
        lines.append("  []")
    lines.append("tags:")
    tag_lines = [f"  - {yaml_string(str(tag))}" for tag in tags if str(tag).strip()]
    lines += tag_lines or ["  []"]
    lines += ["---", "", str(listing.get("description") or "").strip(), ""]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft listings with local Ollama. Does not publish.")
    parser.add_argument("--notes", type=Path, help="CSV with a notes column")
    parser.add_argument("--config", type=Path, default=HERE / "config.json")
    parser.add_argument("--allow-port", action="store_true", help="Allow a local Ollama port other than 11434")
    args = parser.parse_args()
    if not args.notes:
        sys.exit("Pass --notes path\\to\\notes.csv")
    config = load_config(args.config)
    if not args.notes.is_file():
        sys.exit(f"Notes file not found: {args.notes}")
    count = 0
    with args.notes.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            notes = (row.get("notes") or "").strip()
            if not notes:
                continue
            listing = ask_ollama(config, notes, row.get("category") or "", row.get("condition") or "")
            path = write_review(row, listing, (row.get("price") or "").strip(), (row.get("quantity") or "").strip())
            print(f"review draft: {path}")
            count += 1
    print(f"{count} draft(s) in tools/ai-lister/review/. Read them before you copy anything into src/content/products.")
    print("This script did not publish anything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
