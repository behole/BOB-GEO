#!/usr/bin/env python3
import os
import re
import sys
from typing import List
import requests

API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"

def list_assets(store: str, token: str, theme_id: str) -> List[str]:
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token}, timeout=60)
    r.raise_for_status()
    return [a["key"] for a in r.json().get("assets", []) if a.get("key")]

def get_asset(store: str, token: str, theme_id: str, key: str) -> str:
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    r = requests.get(url, params={"asset[key]": key}, headers={"X-Shopify-Access-Token": token}, timeout=60)
    r.raise_for_status()
    return r.json().get("asset", {}).get("value", "")

def main():
    if len(sys.argv) < 2:
        print("Usage: shopify_grep_theme.py <pattern>")
        sys.exit(2)
    pattern = sys.argv[1]
    store = os.getenv("SHOPIFY_STORE")
    token = os.getenv("SHOPIFY_TOKEN")
    theme_id = os.getenv("SHOPIFY_THEME_ID")
    if not (store and token and theme_id):
        print("Set SHOPIFY_STORE, SHOPIFY_TOKEN, SHOPIFY_THEME_ID.")
        sys.exit(2)
    rx = re.compile(pattern, re.I)
    keys = [k for k in list_assets(store, token, theme_id) if k.endswith('.liquid')]
    for key in keys:
        try:
            val = get_asset(store, token, theme_id, key)
        except Exception:
            continue
        if rx.search(val):
            print(key)

if __name__ == '__main__':
    main()

