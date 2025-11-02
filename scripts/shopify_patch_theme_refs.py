#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from typing import Dict, List

import requests


API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")


def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"


def get_asset(store: str, token: str, theme_id: str, key: str) -> str:
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    r = requests.get(url, params={'asset[key]': key}, headers={"X-Shopify-Access-Token": token}, timeout=30)
    r.raise_for_status()
    return r.json().get('asset', {}).get('value', '')


def put_asset(store: str, token: str, theme_id: str, key: str, value: str):
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    payload = {"asset": {"key": key, "value": value}}
    r = requests.put(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, timeout=60)
    r.raise_for_status()


def patch_refs(store: str, token: str, theme_id: str, key: str, mapping: Dict[str, str], confirm: bool):
    before = get_asset(store, token, theme_id, key)
    after = before
    changes = []
    for old, new in mapping.items():
        if old in after:
            after = after.replace(old, new)
            changes.append((old, new))
    if changes:
        if confirm:
            put_asset(store, token, theme_id, key, after)
            print(f"Updated {key} -> {len(changes)} replacements")
        else:
            print(f"DRY RUN: would update {key} -> {len(changes)} replacements")
        for old, new in changes[:5]:
            print(f"  {old} -> {new}")
    else:
        print(f"No matches in {key}")


def main():
    ap = argparse.ArgumentParser(description='Replace file references in theme JSON templates or sections.')
    ap.add_argument('--theme-id', required=True)
    ap.add_argument('--confirm', action='store_true')
    ap.add_argument('--key', action='append', required=True, help='Asset key to patch (e.g., templates/index.json)')
    ap.add_argument('--map', action='append', required=True, help='Mapping old=new (literal substring replacement)')
    args = ap.parse_args()

    store = os.getenv('SHOPIFY_STORE')
    token = os.getenv('SHOPIFY_TOKEN')
    if not store or not token:
        print('Set SHOPIFY_STORE and SHOPIFY_TOKEN env vars.')
        sys.exit(2)

    mapping = {}
    for m in args.map:
        if '=' not in m:
            print(f'Bad mapping: {m}')
            sys.exit(2)
        old, new = m.split('=', 1)
        mapping[old] = new

    for key in args.key:
        patch_refs(store, token, args.theme_id, key, mapping, args.confirm)


if __name__ == '__main__':
    main()
