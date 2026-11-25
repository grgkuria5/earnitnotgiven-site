#!/usr/bin/env python3
"""Turn tools/products-template.csv into product markdown for review.

Writes src/content/products/*.md and does not commit or deploy.
Rows whose SKU starts with EXAMPLE are skipped.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "content" / "products"
CSV_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tools" / "products-template.csv"


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text[:80] or "product"


def yaml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def split_list(value: str) -> list[str]:
    return [part.strip() for part in value.split("|") if part.strip()]


def main() -> int:
    if not CSV_PATH.is_file():
        print(f"CSV not found: {CSV_PATH}", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    written = 0
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            title = (row.get("title") or "").strip()
            sku = (row.get("sku") or "").strip()
            if not title:
                continue
            if sku.upper().startswith("EXAMPLE"):
                print(f"skip example row: {title}")
                continue
            slug = slugify(sku or title)
            target = OUT / f"{slug}.md"
            if target.exists() and "--force" not in sys.argv:
                print(f"exists, skipped (pass --force to replace): {target.name}")
                continue
            specs = []
            for pair in split_list(row.get("specs") or ""):
                if "=" not in pair:
                    continue
                name, value = pair.split("=", 1)
                specs.append((name.strip(), value.strip()))
            images = split_list(row.get("images") or "")
            tags = split_list(row.get("tags") or "")
            bundle_items = split_list(row.get("bundle_items") or "")
            lines = ["---", f"title: {yaml_string(title)}"]
            for key in ("category", "subcategory", "condition"):
                value = (row.get(key) or "").strip()
                if key == "subcategory" and not value:
                    continue
                lines.append(f"{key}: {yaml_string(value)}")
            lines.append(f"price: {(row.get('price') or '0').strip() or '0'}")
            sale = (row.get("sale_price") or "").strip()
            if sale:
                lines.append(f"sale_price: {sale}")
            lines.append(f"quantity: {(row.get('quantity') or '1').strip() or '1'}")
            for key in ("featured", "sample", "draft", "paypal_enabled", "digital", "ai_assisted", "refreshed_tested"):
                lines.append(f"{key}: {'true' if truthy(row.get(key) or '') else 'false'}")
            for key in ("sku", "brand", "summary", "stripe_payment_link", "amazon_url", "etsy_delivery_url", "shipping_note"):
                lines.append(f"{key}: {yaml_string((row.get(key) or '').strip())}")
            product_type = (row.get("product_type") or "standard").strip() or "standard"
            lines.append(f"product_type: {yaml_string(product_type)}")
            savings = (row.get("bundle_savings") or "").strip()
            if savings:
                lines.append(f"bundle_savings: {savings}")
            flash_price = (row.get("flash_price") or "").strip()
            if flash_price:
                lines.append(f"flash_price: {flash_price}")
            for key in ("flash_start", "flash_end", "flash_stripe_link"):
                value = (row.get(key) or "").strip()
                if value:
                    lines.append(f"{key}: {yaml_string(value)}")
            flash_qty = (row.get("flash_qty_limit") or "").strip()
            if flash_qty:
                lines.append(f"flash_qty_limit: {flash_qty}")
            if specs:
                lines.append("specs:")
                for name, value in specs:
                    lines.append(f"  - name: {yaml_string(name)}")
                    lines.append(f"    value: {yaml_string(value)}")
            if images:
                lines.append("images:")
                lines += [f"  - {yaml_string(image)}" for image in images]
            if tags:
                lines.append("tags:")
                lines += [f"  - {yaml_string(tag)}" for tag in tags]
            if bundle_items:
                lines.append("bundle_items:")
                lines += [f"  - {yaml_string(item)}" for item in bundle_items]
            lines.append("---")
            lines.append("")
            lines.append((row.get("description") or "").strip())
            lines.append("")
            # Stay inside the products directory.
            if OUT not in target.resolve().parents:
                print(f"refusing path: {target}", file=sys.stderr)
                return 1
            target.write_text("\n".join(lines), encoding="utf-8")
            print(f"wrote {target.relative_to(ROOT)}")
            written += 1
    print(f"done. {written} file(s). Review them, then commit when you are ready. Nothing was published by this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
