#!/usr/bin/env python3
import os
import re
from datetime import date
from typing import List, Tuple
import requests

API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() not in ("0","false","no")

LD_JSON_RE = re.compile(r"<script[^>]+type=\"application/ld\+json\"[^>]*>([\s\S]*?)</script>", re.I)

def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"

def get_asset(store: str, token: str, theme_id: str, key: str) -> str:
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    r = requests.get(url, params={"asset[key]": key}, headers={"X-Shopify-Access-Token": token}, timeout=60)
    r.raise_for_status()
    return r.json().get("asset", {}).get("value", "")

def put_asset(store: str, token: str, theme_id: str, key: str, value: str):
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    payload = {"asset": {"key": key, "value": value}}
    r = requests.put(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, timeout=60)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        raise RuntimeError(f"PUT {key} failed {r.status_code}: {body}")

def list_assets(store: str, token: str, theme_id: str) -> List[str]:
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token}, timeout=60)
    r.raise_for_status()
    return [a["key"] for a in r.json().get("assets", []) if a.get("key")]

def extract_ld_json(html: str) -> List[Tuple[int,str]]:
    out = []
    for m in LD_JSON_RE.finditer(html):
        start = html[:m.start()].count("\n") + 1
        out.append((start, m.group(0)))
    return out

def main():
    store = os.getenv("SHOPIFY_STORE")
    token = os.getenv("SHOPIFY_TOKEN")
    theme_id = os.getenv("SHOPIFY_THEME_ID")
    if not (store and token and theme_id):
        print("Set SHOPIFY_STORE, SHOPIFY_TOKEN, SHOPIFY_THEME_ID.")
        return
    keys = [k for k in list_assets(store, token, theme_id) if k.endswith('.liquid')]
    candidates = [k for k in keys if k.startswith(('layout/','templates/','sections/'))]
    archive_blocks = []
    edits = []
    for key in candidates:
        val = get_asset(store, token, theme_id, key)
        blocks = extract_ld_json(val)
        if not blocks:
            continue
        archive_blocks.append((key, blocks))
        # Remove blocks
        new_val = LD_JSON_RE.sub("", val)
        if new_val != val:
            edits.append((key, new_val))

    if not archive_blocks:
        print("No inline JSON-LD blocks found.")
        return

    # Build archive snippet
    today = date.today().isoformat()
    snippet_key = f"snippets/legacy-schema-archive-{today}.liquid"
    parts = ["{%- comment -%} Archived inline JSON-LD blocks {%- endcomment -%}"]
    for key, blocks in archive_blocks:
        parts.append(f"\n<!-- From: {key} -->")
        for line_no, html in blocks:
            parts.append(f"<!-- line {line_no} -->\n" + html + "\n")
    archive_content = "\n".join(parts)

    print(f"Will write archive snippet: {snippet_key} ({len(archive_content)} bytes)")
    print(f"Will edit {len(edits)} files to remove inline JSON-LD blocks.")

    if DRY_RUN:
        print("DRY_RUN=true: not writing changes. Set DRY_RUN=false to apply.")
        return

    # Apply changes
    put_asset(store, token, theme_id, snippet_key, archive_content)
    for key, new_val in edits:
        put_asset(store, token, theme_id, key, new_val)
        print("Updated", key)

if __name__ == '__main__':
    main()

