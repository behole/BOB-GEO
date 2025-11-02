#!/usr/bin/env python3
import argparse
import base64
import csv
import io
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

import requests
from requests.exceptions import HTTPError


API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")


def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"


def rest_get(store: str, token: str, path: str, params: Optional[dict] = None) -> dict:
    url = f"{rest_base(store)}{path}"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token})
    r.raise_for_status()
    return r.json()


def rest_put(store: str, token: str, path: str, payload: dict) -> dict:
    url = f"{rest_base(store)}{path}"
    r = requests.put(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def rest_post(store: str, token: str, path: str, payload: dict) -> dict:
    url = f"{rest_base(store)}{path}"
    r = requests.post(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def http_get_bytes(url: str) -> bytes:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content


def load_rename_plan(path: Optional[str]) -> List[dict]:
    if not path:
        # pick latest
        import glob
        paths = sorted(glob.glob("audits/brushonblock-rename-plan-*.csv"))
        if not paths:
            raise SystemExit("No rename plan CSV found. Run prepare script.")
        path = paths[-1]
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def canonical(url: str) -> str:
    url = url.split('#', 1)[0]
    url = url.split('?', 1)[0]
    return url


def choose_initial_items(rows: List[dict], max_items: int) -> List[dict]:
    picks = []
    targets = [
        ('star_star_star_star_star.svg', 'brush-on-block-stars.svg'),
        ('BOB_logo_horiz_2022', 'brush-on-block-logo-horizontal.svg'),
    ]
    for needle, suggested in targets:
        for r in rows:
            if needle.lower() in r['current_filename'].lower():
                r = dict(r)
                r['suggested_filename'] = suggested
                picks.append(r)
                break
        if len(picks) >= max_items:
            break
    return picks[:max_items]


def list_theme_asset_keys(store: str, token: str, theme_id: str) -> List[str]:
    j = rest_get(store, token, f"/themes/{theme_id}/assets.json")
    keys = []
    for a in j.get('assets', []):
        k = a.get('key')
        if not k:
            continue
        # Focus on Liquid templates/snippets/sections/layout and settings_data
        if k.endswith('.liquid') or k == 'config/settings_data.json':
            keys.append(k)
    return keys


def get_asset_value(store: str, token: str, theme_id: str, key: str) -> Optional[str]:
    url = f"/themes/{theme_id}/assets.json?asset[key]={key}"
    r = requests.get(rest_base(store) + url, headers={"X-Shopify-Access-Token": token})
    r.raise_for_status()
    data = r.json().get('asset', {})
    if 'value' in data:
        return data['value']
    if 'attachment' in data:
        # Binary; skip
        return None
    return None


def put_asset_value(store: str, token: str, theme_id: str, key: str, value: str):
    payload = {"asset": {"key": key, "value": value}}
    rest_put(store, token, f"/themes/{theme_id}/assets.json", payload)


def upload_file_to_files(store: str, token: str, filename: str, content: bytes) -> str:
    payload = {"file": {"filename": filename, "attachment": base64.b64encode(content).decode('ascii')}}
    j = rest_post(store, token, "/files.json", payload)
    return j['file']['url']


def upload_asset_to_theme(store: str, token: str, theme_id: str, filename: str, content: bytes, content_type: Optional[str] = None):
    key = f"assets/{filename}"
    payload = {"asset": {"key": key, "attachment": base64.b64encode(content).decode('ascii')}}
    if content_type:
        payload['asset']['content_type'] = content_type
    rest_put(store, token, f"/themes/{theme_id}/assets.json", payload)
    # Theme asset URL must be resolved at render-time via asset_url
    return key


def apply_renames(store: str, token: str, theme_id: str, items: List[dict], confirm: bool, limit: int) -> List[Tuple[str, str, str]]:
    # returns list of (old_filename, new_filename, new_url)
    changed: List[Tuple[str, str, str]] = []
    asset_keys = list_theme_asset_keys(store, token, theme_id)
    for i, r in enumerate(items[:limit], 1):
        old_url = canonical(r['image_url'])
        old_name = r['current_filename']
        new_name = r['suggested_filename']
        try:
            content = http_get_bytes(old_url)
        except Exception as e:
            print(f"Skip {old_name}: failed to download ({e})")
            continue
        # Upload new file into Files library
        try:
            new_url = upload_file_to_files(store, token, new_name, content)
        except HTTPError as e:
            # Fallback: upload as theme asset
            print(f"Files API upload failed for {new_name}, falling back to theme asset. ({e})")
            # Guess content-type by extension
            ct = 'image/svg+xml' if new_name.lower().endswith('.svg') else None
            asset_key = upload_asset_to_theme(store, token, theme_id, new_name, content, content_type=ct)
            # Use Liquid asset_url expression as replacement token in .liquid files
            new_url = f"{{{{ '{new_name}' | asset_url }}}}"

        # Update theme code references (URLs and filename literals)
        for key in asset_keys:
            try:
                val = get_asset_value(store, token, theme_id, key)
            except Exception:
                continue
            if not isinstance(val, str):
                continue
            new_val = val
            if old_url in new_val:
                new_val = new_val.replace(old_url, new_url)
            # Replace file_url usage like 'old_name' | file_url with asset_url if we fell back
            if old_name in new_val:
                if "asset_url" in new_url:
                    # Replace "'old' | file_url" with "'new' | asset_url"
                    new_val = re.sub(rf"(['\"])\s*{re.escape(old_name)}\s*(['\"])\s*\|\s*file_url",
                                     lambda m: f"'{new_name}' | asset_url", new_val)
                else:
                    new_val = new_val.replace(old_name, new_name)
            if new_val != val:
                if confirm:
                    put_asset_value(store, token, theme_id, key, new_val)
                    print(f"Updated {key}")
                else:
                    print(f"DRY RUN: would update {key}")
        changed.append((old_name, new_name, new_url))
        print(f"Prepared rename {old_name} -> {new_name}")
    return changed


def main():
    ap = argparse.ArgumentParser(description="Apply file renames to a staging theme by uploading new Files and updating theme code references.")
    ap.add_argument('--theme-id', required=True, help='Target staging theme ID (unpublished)')
    ap.add_argument('--rename-plan', help='Path to rename plan CSV')
    ap.add_argument('--limit', type=int, default=5, help='Max number of items to process')
    ap.add_argument('--confirm', action='store_true', help='Apply changes (default dry-run)')
    args = ap.parse_args()

    store = os.getenv('SHOPIFY_STORE')
    token = os.getenv('SHOPIFY_TOKEN')
    if not store or not token:
        print('Set SHOPIFY_STORE and SHOPIFY_TOKEN env vars.')
        sys.exit(2)

    rows = load_rename_plan(args.rename_plan)
    items = choose_initial_items(rows, args.limit)
    if not items:
        print('No initial items found in rename plan.')
        sys.exit(0)

    changed = apply_renames(store, token, args.theme_id, items, confirm=args.confirm, limit=args.limit)
    # Log
    os.makedirs('audits', exist_ok=True)
    import datetime
    out = f"audits/rename-applied-{datetime.date.today().isoformat()}.csv"
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['old_filename', 'new_filename', 'new_url'])
        for o, n, u in changed:
            w.writerow([o, n, u])
    print(out)


if __name__ == '__main__':
    main()
