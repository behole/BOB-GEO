#!/usr/bin/env python3
import argparse
import csv
import os
import sys
import time
from typing import List, Dict

import requests
from requests.exceptions import HTTPError


API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")


def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"


def rest_get(store: str, token: str, path: str) -> dict:
    url = f"{rest_base(store)}{path}"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token})
    r.raise_for_status()
    return r.json()


def rest_put(store: str, token: str, path: str, payload: dict) -> dict:
    url = f"{rest_base(store)}{path}"
    r = requests.put(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def list_all_products(store: str, token: str) -> List[dict]:
    products = []
    since_id = 0
    while True:
        data = rest_get(store, token, f"/products.json?limit=250&since_id={since_id}&fields=id,title,status,handle,images")
        batch = data.get("products", [])
        if not batch:
            break
        products.extend(batch)
        since_id = batch[-1]["id"]
    return products


def fill_missing_product_alts(store: str, token: str, confirm: bool, limit: int, sleep_sec: float = 0.15) -> int:
    products = list_all_products(store, token)
    queued = 0
    updates_csv_rows = []
    for p in products:
        pid = p["id"]
        title = (p.get("title") or "").strip()
        if not title:
            continue
        for img in p.get("images", []):
            alt = (img.get("alt") or "").strip()
            if alt:
                continue
            image_id = img.get("id")
            payload = {"image": {"id": image_id, "alt": title}}
            path = f"/products/{pid}/images/{image_id}.json"
            if confirm:
                try:
                    rest_put(store, token, path, payload)
                except HTTPError as e:
                    # Log and continue
                    sys.stderr.write(f"Failed {path}: {e}\n")
                    continue
                time.sleep(sleep_sec)
            else:
                print("DRY RUN:", path, payload)
            queued += 1
            updates_csv_rows.append({
                "product_id": pid,
                "product_title": title,
                "image_id": image_id,
                "new_alt": title,
            })
            if queued >= limit:
                break
        if queued >= limit:
            break

    # Write a quick log CSV
    os.makedirs("audits", exist_ok=True)
    import datetime
    out = f"audits/shopify-product-alt-fills-{datetime.date.today().isoformat()}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["product_id", "product_title", "image_id", "new_alt"])
        w.writeheader()
        w.writerows(updates_csv_rows)
    print(out)
    return queued


def main():
    ap = argparse.ArgumentParser(description="Fill empty product image ALT with product title")
    ap.add_argument("--confirm", action="store_true", help="Apply changes (without this it is dry-run)")
    ap.add_argument("--limit", type=int, default=200, help="Max number of image updates to perform")
    args = ap.parse_args()

    store = os.getenv("SHOPIFY_STORE")
    token = os.getenv("SHOPIFY_TOKEN")
    if not store or not token:
        print("Set SHOPIFY_STORE and SHOPIFY_TOKEN env vars.")
        sys.exit(2)

    count = fill_missing_product_alts(store, token, confirm=args.confirm, limit=args.limit)
    mode = "APPLIED" if args.confirm else "DRY RUN" 
    print(f"{mode}: queued {count} product image ALT updates")


if __name__ == "__main__":
    main()

