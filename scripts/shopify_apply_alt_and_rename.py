#!/usr/bin/env python3
"""
Shopify apply script (dry-run by default).

What it does:
- Reads audits/brushonblock-images-unique-*.csv and prepares ALT updates.
- Optionally, reads audits/brushonblock-rename-plan-*.csv and prepares rename swaps.

How to run (later with access):
- export SHOPIFY_STORE="yourstore"  # without .myshopify.com
- export SHOPIFY_TOKEN="shpat_..."  # Admin API token
- python3 scripts/shopify_apply_alt_and_rename.py --apply-alts --apply-renames --theme-staging-id 123456789 --confirm

Defaults:
- DRY RUN unless --confirm is passed.
- API version set to 2024-10. Adjust if needed.
"""
import argparse
import base64
import csv
import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional

import requests
from requests.exceptions import HTTPError, RequestException


API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")


def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        print(f"Missing env: {name}")
        sys.exit(2)
    return v


def latest(path_glob: str) -> str:
    paths = sorted(glob.glob(path_glob))
    if not paths:
        print(f"No files match {path_glob}")
        sys.exit(1)
    return paths[-1]


def canon(url: str) -> str:
    return url.split("?", 1)[0]


def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"


def rest_get(store: str, token: str, path: str, params: Optional[dict] = None) -> dict:
    url = f"{rest_base(store)}{path}"
    try:
        r = requests.get(url, headers={"X-Shopify-Access-Token": token})
        r.raise_for_status()
        return r.json()
    except HTTPError as e:
        body = getattr(e.response, 'text', '') if hasattr(e, 'response') and e.response is not None else ''
        print(f"GET {path} failed: {e} {body[:200]}")
        raise


def rest_put(store: str, token: str, path: str, payload: dict) -> dict:
    url = f"{rest_base(store)}{path}"
    try:
        r = requests.put(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
        r.raise_for_status()
        return r.json()
    except HTTPError as e:
        body = getattr(e.response, 'text', '') if hasattr(e, 'response') and e.response is not None else ''
        print(f"PUT {path} failed: {e} {body[:200]}")
        raise


def rest_post(store: str, token: str, path: str, payload: dict) -> dict:
    url = f"{rest_base(store)}{path}"
    try:
        r = requests.post(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
        r.raise_for_status()
        return r.json()
    except HTTPError as e:
        body = getattr(e.response, 'text', '') if hasattr(e, 'response') and e.response is not None else ''
        print(f"POST {path} failed: {e} {body[:200]}")
        raise


def load_unique_csv(path: Optional[str]) -> List[dict]:
    if not path:
        path = latest("audits/brushonblock-images-unique-*.csv")
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_rename_csv(path: Optional[str]) -> List[dict]:
    if not path:
        path = latest("audits/brushonblock-rename-plan-*.csv")
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def list_products_with_images(store: str, token: str) -> List[dict]:
    products = []
    page_info = None
    # Use REST pagination via since_id or page_info; for simplicity, use limit=250 and since_id.
    since_id = 0
    while True:
        url = f"/products.json?limit=250&since_id={since_id}&fields=id,title,handle,images"
        data = rest_get(store, token, url)
        batch = data.get('products', [])
        if not batch:
            break
        products.extend(batch)
        since_id = batch[-1]['id']
    return products


def filename_only(url: str) -> str:
    u = canon(url)
    return u.rstrip('/').split('/')[-1]


def map_product_images_by_src(products: List[dict]):
    # Return two maps: by full src and by filename when unique
    m_full: Dict[str, dict] = {}
    fname_buckets: Dict[str, List[dict]] = {}
    for p in products:
        pid = p['id']
        for img in p.get('images', []):
            src = canon(img.get('src', ''))
            if not src:
                continue
            rec = {"product_id": pid, "image": img, "src": src}
            m_full[src] = rec
            fname = filename_only(src)
            fname_buckets.setdefault(fname, []).append(rec)
    m_fname_unique: Dict[str, dict] = {k: v[0] for k, v in fname_buckets.items() if len(v) == 1}
    return m_full, m_fname_unique


def update_product_image_alt(store: str, token: str, product_id: int, image_id: int, new_alt: str, dry_run: bool):
    path = f"/products/{product_id}/images/{image_id}.json"
    payload = {"image": {"id": image_id, "alt": new_alt}}
    if dry_run:
        print("DRY RUN: PUT", path, json.dumps(payload))
        return
    rest_put(store, token, path, payload)


def list_pages(store: str, token: str) -> List[dict]:
    pages = []
    since_id = 0
    while True:
        data = rest_get(store, token, f"/pages.json?limit=250&since_id={since_id}&fields=id,title,body_html")
        batch = data.get('pages', [])
        if not batch:
            break
        pages.extend(batch)
        since_id = batch[-1]['id']
    return pages


def list_blogs(store: str, token: str) -> List[dict]:
    data = rest_get(store, token, "/blogs.json")
    return data.get('blogs', [])


def list_articles(store: str, token: str, blog_id: int) -> List[dict]:
    arts = []
    since_id = 0
    while True:
        data = rest_get(store, token, f"/blogs/{blog_id}/articles.json?limit=250&since_id={since_id}&fields=id,title,body_html")
        batch = data.get('articles', [])
        if not batch:
            break
        arts.extend(batch)
        since_id = batch[-1]['id']
    return arts


def replace_img_alts_in_html(html: str, mapping: Dict[str, str], add_only: bool = False) -> str:
    # Naive replace: for each src canonical, ensure alt exists/updated
    # We will replace alt="..." or insert alt="..." after src
    for src, alt in mapping.items():
        # Match the img tag with this src (allow query strings in content)
        pattern = re.compile(rf"(<img[^>]*?src=\"{re.escape(src)}[^\"]*\"[^>]*)(>)", re.I)

        def repl(m):
            tag_open = m.group(1)
            end = m.group(2)
            if re.search(r"\balt=\"[^\"]*\"", tag_open, re.I):
                if add_only:
                    # Leave existing alt intact
                    return tag_open + end
                else:
                    tag_open2 = re.sub(r"\balt=\"[^\"]*\"", f'alt="{alt}"', tag_open, flags=re.I)
                    return tag_open2 + end
            else:
                return tag_open + f' alt="{alt}"' + end

        html = pattern.sub(repl, html)
    return html


def apply_alt_updates(store: str, token: str, unique_csv: str, confirm: bool, limit: Optional[int], update_products: bool = True, update_pages: bool = True, update_articles: bool = True):
    dry = not confirm
    if limit is None:
        limit = 50 if dry else 25
    rows = load_unique_csv(unique_csv)
    # Build mapping for product image updates
    candidates = [r for r in rows if r['suggested_alt'].strip()]
    # Products
    if update_products:
        products = list_products_with_images(store, token)
        img_map_full, img_map_fname = map_product_images_by_src(products)
        updates = 0
        for r in candidates:
            src = canon(r['image_url'])
            s_alt = r['suggested_alt'].strip()
            match = None
            if src in img_map_full:
                match = img_map_full[src]
            else:
                fname = filename_only(src)
                if fname in img_map_fname:
                    match = img_map_fname[fname]
            if match is not None:
                prod_id = match['product_id']
                img = match['image']
                if (img.get('alt') or '') != s_alt:
                    update_product_image_alt(store, token, prod_id, img['id'], s_alt, dry)
                    updates += 1
                    if updates >= limit:
                        break
        print(f"Product images queued: {updates}")
    else:
        print("Product image updates skipped by flag.")

    # Pages and articles: build a mapping src->alt and rewrite HTML
    page_updates = 0
    mapping = {canon(r['image_url']): r['suggested_alt'].strip() for r in candidates}
    # Pages
    if update_pages:
        for p in list_pages(store, token):
            body = p.get('body_html') or ''
            new_body = replace_img_alts_in_html(body, mapping, add_only=True)
            if new_body != body:
                if dry:
                    title = p.get('title', '')
                    print(f"DRY RUN: UPDATE PAGE id={p['id']} title=\"{title}\"")
                else:
                    rest_put(store, token, f"/pages/{p['id']}.json", {"page": {"id": p['id'], "body_html": new_body}})
                page_updates += 1
                if page_updates >= limit:
                    break
        print(f"Pages queued: {page_updates}")
    else:
        print("Page updates skipped by flag.")

    # Articles
    art_updates = 0
    if update_articles:
        for b in list_blogs(store, token):
            for a in list_articles(store, token, b['id']):
                body = a.get('body_html') or ''
                new_body = replace_img_alts_in_html(body, mapping, add_only=True)
                if new_body != body:
                    if dry:
                        print("DRY RUN: PUT /blogs/{blog_id}/articles/{id}.json", b['id'], a['id'])
                    else:
                        rest_put(store, token, f"/blogs/{b['id']}/articles/{a['id']}.json", {"article": {"id": a['id'], "body_html": new_body}})
                    art_updates += 1
                    if art_updates >= limit:
                        break
            if art_updates >= limit:
                break
        print(f"Articles queued: {art_updates}")
    else:
        print("Blog article updates skipped by flag.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--unique-csv', help='Path to images unique CSV')
    ap.add_argument('--rename-csv', help='Path to rename plan CSV')
    ap.add_argument('--apply-alts', action='store_true')
    ap.add_argument('--apply-renames', action='store_true')
    ap.add_argument('--theme-staging-id', type=str, help='Theme ID for code updates (renames)')
    ap.add_argument('--confirm', action='store_true', help='Actually make changes (default dry-run)')
    ap.add_argument('--limit', type=int, help='Limit updates per category (products/pages/articles). Default: 50 dry-run, 25 confirm')
    ap.add_argument('--skip-products', action='store_true', help='Skip product media alt updates')
    ap.add_argument('--skip-pages', action='store_true', help='Skip Page body_html alt updates')
    ap.add_argument('--skip-articles', action='store_true', help='Skip Blog Article body_html alt updates')
    args = ap.parse_args()

    store = os.getenv('SHOPIFY_STORE')
    token = os.getenv('SHOPIFY_TOKEN')

    if args.apply_alts:
        if not store or not token:
            print('Set SHOPIFY_STORE and SHOPIFY_TOKEN env vars before applying.')
            sys.exit(2)
        apply_alt_updates(
            store,
            token,
            args.unique_csv,
            args.confirm,
            args.limit,
            update_products=not args.skip_products,
            update_pages=not args.skip_pages,
            update_articles=not args.skip_articles,
        )

    if args.apply_renames:
        print('Rename workflow is more invasive and will:')
        print('- upload new files, swap product media, and rewrite page/article HTML')
        print('- updating theme assets may require PR review for Liquid changes')
        print('This module is scaffolded; enable once ALT updates are done.')


if __name__ == '__main__':
    main()
