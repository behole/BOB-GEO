#!/usr/bin/env python3
import os
import re
from typing import List
import requests

API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"

def list_assets(store: str, token: str, theme_id: str) -> List[str]:
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token}, timeout=60)
    r.raise_for_status()
    assets = r.json().get("assets", [])
    return [a["key"] for a in assets if a.get("key")]

def get_asset(store: str, token: str, theme_id: str, key: str) -> str:
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    r = requests.get(url, params={"asset[key]": key}, headers={"X-Shopify-Access-Token": token}, timeout=60)
    r.raise_for_status()
    return r.json().get("asset", {}).get("value", "")

def main():
    store = os.getenv("SHOPIFY_STORE")
    token = os.getenv("SHOPIFY_TOKEN")
    theme_id = os.getenv("SHOPIFY_THEME_ID")
    if not (store and token and theme_id):
        print("Set SHOPIFY_STORE, SHOPIFY_TOKEN, SHOPIFY_THEME_ID.")
        return
    keys = list_assets(store, token, theme_id)
    # Inspect likely Liquid files
    inspect = [k for k in keys if k.endswith('.liquid') and (k.startswith('layout/') or k.startswith('sections/') or k.startswith('templates/') or k.startswith('snippets/'))]
    pattern = re.compile(r'type\s*=\s*\"application/ld\+json\"', re.I)
    hits = []
    for key in inspect:
        try:
            val = get_asset(store, token, theme_id, key)
            if pattern.search(val):
                # summarize locations
                lines = []
                for i, line in enumerate(val.splitlines(), 1):
                    if 'application/ld+json' in line:
                        lines.append(i)
                hits.append((key, lines[:10]))
        except Exception:
            continue
    if not hits:
        print("No inline JSON-LD blocks found in theme.")
        return
    print("Found inline JSON-LD in:")
    for key, lines in hits:
        print(f"- {key} @ lines {', '.join(map(str, lines))}")

if __name__ == '__main__':
    main()

