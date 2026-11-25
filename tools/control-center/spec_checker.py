"""Pluggable spec lookups. Official pages open in the browser. No page scraping."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ALLOWED_HOSTS = {
    "www.dell.com",
    "support.hp.com",
    "pcsupport.lenovo.com",
    "checkcoverage.apple.com",
    "support.apple.com",
    "everymac.com",
    "support.microsoft.com",
    "www.asus.com",
    "www.acer.com",
    "www.msi.com",
    "support.dynabook.com",
    "www.samsung.com",
    "support.google.com",
    "www.imei.info",
    "www.gsma.com",
    "www.cisco.com",
    "cway.cisco.com",
    "www.netgear.com",
    "www.tp-link.com",
    "help.ui.com",
    "techspecs.ui.com",
    "support.brother.com",
    "epson.com",
    "www.techpowerup.com",
    "ark.intel.com",
    "www.amd.com",
    "www.crucial.com",
    "www.kingston.com",
    "www.westerndigital.com",
    "semiconductor.samsung.com",
    "world.openfoodfacts.org",
    "api.upcitemdb.com",
}

PROVIDERS = [
    {"id": "dell", "label": "Dell service tag", "group": "PCs", "hint": "7-character service tag",
     "links": [("Dell support for this tag", "https://www.dell.com/support/home/en-us/product-support/servicetag/{q}")]},
    {"id": "hp", "label": "HP serial or product number", "group": "PCs", "hint": "Serial or product number",
     "links": [("HP support search", "https://support.hp.com/us-en/search?q={q}")]},
    {"id": "lenovo", "label": "Lenovo serial or MTM", "group": "PCs", "hint": "Serial or machine type model, such as 20ABC1CD",
     "links": [("Lenovo warranty lookup", "https://pcsupport.lenovo.com/us/en/warranty-lookup#/"),
               ("Lenovo search", "https://pcsupport.lenovo.com/us/en/search/#/{q}")]},
    {"id": "apple-serial", "label": "Apple serial", "group": "Apple", "hint": "Mac or iPhone serial",
     "links": [("Apple Check Coverage", "https://checkcoverage.apple.com/us/en/?sn={q}"),
               ("EveryMac lookup", "https://everymac.com/ultimate-mac-lookup/?search_keywords={q}")]},
    {"id": "apple-model", "label": "Mac model identifier", "group": "Apple", "hint": "Such as MacBookPro16,1 or Mac14,2",
     "links": [("Apple support search", "https://support.apple.com/kb/index?page=search&q={q}"),
               ("EveryMac model search", "https://everymac.com/ultimate-mac-lookup/?search_keywords={q}")]},
    {"id": "surface", "label": "Microsoft Surface serial", "group": "PCs", "hint": "Surface serial",
     "links": [("Microsoft support search", "https://support.microsoft.com/en-us/search/results?query={q}")]},
    {"id": "asus", "label": "Asus serial", "group": "PCs", "hint": "Serial",
     "links": [("Asus warranty inquiry", "https://www.asus.com/support/warranty-status-inquiry/"),
               ("Asus support search", "https://www.asus.com/us/support/search/?q={q}")]},
    {"id": "acer", "label": "Acer serial or SNID", "group": "PCs", "hint": "Serial or SNID",
     "links": [("Acer product support", "https://www.acer.com/us-en/support/product-support/{q}")]},
    {"id": "msi", "label": "MSI serial", "group": "PCs", "hint": "Serial",
     "links": [("MSI warranty inquiry", "https://www.msi.com/support/download"),
               ("MSI support search", "https://www.msi.com/search/{q}")]},
    {"id": "dynabook", "label": "Toshiba / Dynabook serial", "group": "PCs", "hint": "Serial",
     "links": [("Dynabook support", "https://support.dynabook.com/support/home?q={q}")]},
    {"id": "samsung", "label": "Samsung model or serial", "group": "Phones and PCs", "hint": "Model or serial",
     "links": [("Samsung support search", "https://www.samsung.com/us/support/search/?keyword={q}")]},
    {"id": "pixel", "label": "Google Pixel", "group": "Phones", "hint": "Serial or IMEI",
     "links": [("Pixel support", "https://support.google.com/pixelphone/answer/3335221")]},
    {"id": "imei", "label": "iPhone or Android IMEI", "group": "Phones", "hint": "15-digit IMEI. TAC is the first 8 digits.",
     "links": [("Free IMEI info page", "https://www.imei.info/?imei={q}"),
               ("GSMA IMEI overview", "https://www.gsma.com/about-us/workinggroups/terminal-steering-group/"),
               ("Apple Check Coverage", "https://checkcoverage.apple.com/us/en/?sn={q}")]},
    {"id": "cisco", "label": "Cisco serial or PID", "group": "Network", "hint": "Serial or product ID such as C9300-24P",
     "links": [("Cisco serial check", "https://cway.cisco.com/sncheck/"),
               ("Cisco support search / PID sheet", "https://www.cisco.com/c/en/us/search.html?q={q}")]},
    {"id": "netgear", "label": "Netgear model or serial", "group": "Network", "hint": "Model",
     "links": [("Netgear support", "https://www.netgear.com/support/product/{q}")]},
    {"id": "tplink", "label": "TP-Link model", "group": "Network", "hint": "Model",
     "links": [("TP-Link search", "https://www.tp-link.com/us/search/?q={q}")]},
    {"id": "ubiquiti", "label": "Ubiquiti model", "group": "Network", "hint": "Model",
     "links": [("Ubiquiti tech specs", "https://techspecs.ui.com/"),
               ("Ubiquiti help search", "https://help.ui.com/hc/en-us/search?query={q}")]},
    {"id": "brother", "label": "Brother printer model", "group": "Printers", "hint": "Model",
     "links": [("Brother support search", "https://support.brother.com/g/b/productsearch.aspx?c=us&lang=en&content=ml&qt={q}")]},
    {"id": "epson", "label": "Epson printer model", "group": "Printers", "hint": "Model",
     "links": [("Epson support", "https://epson.com/Support/{q}")]},
    {"id": "monitor", "label": "Monitor model", "group": "Parts", "hint": "Brand and model, such as Dell U2723QE",
     "links": [("Dell monitor search", "https://www.dell.com/support/home/en-us/search?q={q}"),
               ("HP product search", "https://support.hp.com/us-en/search?q={q}")]},
    {"id": "gpu", "label": "GPU model", "group": "Parts", "hint": "Such as RTX 3060",
     "links": [("TechPowerUp GPU database", "https://www.techpowerup.com/gpu-specs/?ajaxsrch={q}")]},
    {"id": "cpu-intel", "label": "Intel CPU", "group": "Parts", "hint": "Such as i5-12400",
     "links": [("Intel ARK search", "https://ark.intel.com/content/www/us/en/ark/search.html?q={q}")]},
    {"id": "cpu-amd", "label": "AMD CPU", "group": "Parts", "hint": "Such as Ryzen 5 5600",
     "links": [("AMD search", "https://www.amd.com/en/search/site-search.html#q={q}")]},
    {"id": "storage", "label": "RAM or SSD model", "group": "Parts", "hint": "Model from the label",
     "links": [("Crucial", "https://www.crucial.com/search?search={q}"),
               ("Kingston", "https://www.kingston.com/en/search?query={q}"),
               ("Western Digital", "https://www.westerndigital.com/search?q={q}"),
               ("Samsung semiconductor", "https://semiconductor.samsung.com/search/?query={q}")]},
    {"id": "upc", "label": "UPC or EAN barcode", "group": "Barcode", "hint": "12 or 13 digit code. Uses Open Food Facts, and UPCitemdb only if you set a free-tier key.",
     "links": []},
]


def providers() -> list[dict]:
    return [{"id": row["id"], "label": row["label"], "group": row["group"], "hint": row["hint"]} for row in PROVIDERS]


def _clean(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _check_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"blocked lookup URL host: {parsed.hostname}")
    return url


def provider_by_id(provider_id: str) -> dict:
    for row in PROVIDERS:
        if row["id"] == provider_id:
            return row
    raise KeyError(provider_id)


def build_links(provider_id: str, identifier: str) -> list[dict]:
    row = provider_by_id(provider_id)
    query = urllib.parse.quote(_clean(identifier) or identifier.strip())
    links = []
    for label, template in row["links"]:
        url = _check_url(template.format(q=query))
        links.append({"label": label, "url": url})
    return links


def tac_lookup(imei: str, tac_file: Path) -> dict | None:
    digits = re.sub(r"\D", "", imei)
    if len(digits) < 8 or not tac_file.is_file():
        return None
    tac = digits[:8]
    try:
        rows = json.loads(tac_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for row in rows if isinstance(rows, list) else []:
        if str(row.get("tac")) == tac and not row.get("sample"):
            return {"brand": row.get("brand", ""), "model": row.get("model", ""), "tac": tac, "source": "local-tac-file"}
    return None


def cache_path(folder: Path, provider_id: str, identifier: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", _clean(identifier))[:80] or "item"
    return folder / f"{provider_id}-{safe}.json"


def read_cache(folder: Path, provider_id: str, identifier: str) -> dict | None:
    path = cache_path(folder, provider_id, identifier)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_cache(folder: Path, provider_id: str, identifier: str, payload: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = cache_path(folder, provider_id, identifier)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def lookup_upc(code: str, api_key: str = "") -> dict:
    digits = re.sub(r"\D", "", code)
    result = {"identifier": digits, "source": "", "name": "", "brand": "", "sample": False}
    off = urllib.request.Request(
        f"https://world.openfoodfacts.org/api/v2/product/{digits}.json",
        headers={"user-agent": "EarnItNotGiven-SpecChecker/1.0"},
    )
    try:
        with urllib.request.urlopen(off, timeout=12) as response:
            body = json.loads(response.read().decode())
        product = body.get("product") or {}
        if product:
            result.update({"source": "open-food-facts", "name": product.get("product_name") or "", "brand": product.get("brands") or ""})
            return result
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    url = "https://api.upcitemdb.com/prod/trial/lookup?upc=" + urllib.parse.quote(digits)
    headers = {"user-agent": "EarnItNotGiven-SpecChecker/1.0"}
    if api_key:
        url = "https://api.upcitemdb.com/prod/v1/lookup?upc=" + urllib.parse.quote(digits)
        headers["user_key"] = api_key
        headers["key_type"] = "3scale"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            body = json.loads(response.read().decode())
        items = body.get("items") or []
        if items:
            result.update({"source": "upcitemdb", "name": items[0].get("title") or "", "brand": items[0].get("brand") or ""})
    except (OSError, ValueError, json.JSONDecodeError):
        result["note"] = "No free barcode record. Paste the package text and use Normalize."
    return result


SUGGESTED_CATEGORY = {
    "dell": ("computers", "laptops"),
    "hp": ("computers", "laptops"),
    "lenovo": ("computers", "laptops"),
    "apple-serial": ("phones", "iphone"),
    "apple-model": ("computers", "laptops"),
    "surface": ("computers", "laptops"),
    "asus": ("computers", "laptops"),
    "acer": ("computers", "laptops"),
    "msi": ("computers", "laptops"),
    "dynabook": ("computers", "laptops"),
    "samsung": ("phones", "android"),
    "pixel": ("phones", "android"),
    "imei": ("phones", "android"),
    "cisco": ("networking", "cisco"),
    "netgear": ("networking", "routers"),
    "tplink": ("networking", "routers"),
    "ubiquiti": ("networking", "wifi"),
    "brother": ("printers", ""),
    "epson": ("printers", ""),
    "monitor": ("computers", "monitors"),
    "gpu": ("parts", "gpus"),
    "cpu-intel": ("parts", "cpus"),
    "cpu-amd": ("parts", "cpus"),
    "storage": ("parts", "storage"),
    "upc": ("accessories", ""),
}


def suggest_category(provider_id: str) -> dict:
    category, subcategory = SUGGESTED_CATEGORY.get(provider_id, ("computers", ""))
    return {"category": category, "subcategory": subcategory, "provider": provider_id}


SAMPLE_SPECS = {
    "sample": True,
    "provider": "dell",
    "identifier": "SAMPLE7X",
    "maker": "Dell",
    "kind": "service-tag",
    "support_url": "https://www.dell.com/support/home/en-us/product-support/servicetag/SAMPLE7X",
    "system": "SAMPLE Latitude",
    "cpu": "SAMPLE Intel Core i5",
    "ram_gb": 16,
    "disk": "SAMPLE 512 GB SSD",
    "note": "SAMPLE DATA. Not read from a machine and not downloaded from Dell.",
}


def local_wmi_script() -> str:
    return r"""
$ErrorActionPreference = 'Stop'
$cs = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$ram = [math]::Round(((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB), 1)
$disks = Get-CimInstance Win32_DiskDrive | ForEach-Object { "$($_.Model) $([math]::Round($_.Size/1GB,0)) GB" }
$gpu = (Get-CimInstance Win32_VideoController | Select-Object -First 1).Name
$bios = Get-CimInstance Win32_BIOS
[pscustomobject]@{
  sample = $false
  identifier = $bios.SerialNumber
  maker = $cs.Manufacturer
  system = $cs.Model
  cpu = $cpu.Name
  ram_gb = $ram
  disk = ($disks -join '; ')
  gpu = $gpu
  bios_serial = $bios.SerialNumber
  note = 'Read on this PC with WMI/CIM. Not sent anywhere.'
} | ConvertTo-Json -Compress
""".strip()


def read_local_windows() -> dict:
    import sys
    if sys.platform != "win32":
        raise RuntimeError("WMI/CIM runs on the Windows bench PC. This session is not that PC, so no hardware was read.")
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", local_wmi_script()],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-300:] or "PowerShell could not read this PC.")
    return json.loads(completed.stdout)


def read_android_adb() -> dict:
    if not shutil.which("adb"):
        raise RuntimeError("adb is not installed. It is optional. Install platform-tools and enable USB debugging, then try again.")
    props = subprocess.run(["adb", "shell", "getprop"], capture_output=True, text=True, timeout=20, check=False)
    if props.returncode != 0:
        raise RuntimeError(props.stderr[-300:] or "adb could not read the phone. Check the USB cable and debugging prompt.")
    text = props.stdout

    def prop(name: str) -> str:
        match = re.search(rf"\[{re.escape(name)}\]:\s*\[(.*?)\]", text)
        return match.group(1) if match else ""

    return {
        "sample": False,
        "maker": prop("ro.product.manufacturer"),
        "system": prop("ro.product.model"),
        "identifier": prop("ro.serialno") or prop("ro.boot.serialno"),
        "note": "Read with adb on this PC. Not sent anywhere.",
    }
