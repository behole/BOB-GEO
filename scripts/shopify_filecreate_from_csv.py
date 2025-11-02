#!/usr/bin/env python3
import csv
import os
import sys
from typing import Optional
import requests

API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

def graphql(store: str, token: str, query: str, variables: dict) -> dict:
    url = f"https://{store}.myshopify.com/admin/api/{API_VERSION}/graphql.json"
    r = requests.post(url, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, json={"query": query, "variables": variables}, timeout=60)
    r.raise_for_status()
    return r.json()

def file_create_image(store: str, token: str, filename: str, source_url: str) -> Optional[str]:
    q = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files { __typename ... on MediaImage { id image { url altText } } ... on GenericFile { id url } }
        userErrors { field message }
      }
    }
    """
    vars = {"files": [{"filename": filename, "originalSource": source_url}]}
    j = graphql(store, token, q, vars)
    errs = j.get("data",{}).get("fileCreate",{}).get("userErrors")
    if errs:
        print("GraphQL userErrors:", errs)
    files = j.get("data",{}).get("fileCreate",{}).get("files",[])
    if not files:
        return None
    f = files[0]
    if f.get("__typename") == "MediaImage":
        return f.get("image",{}).get("url")
    return f.get("url")

def main():
    if len(sys.argv) < 2:
        print("Usage: shopify_filecreate_from_csv.py <batch_csv>")
        sys.exit(2)
    store = os.getenv("SHOPIFY_STORE")
    token = os.getenv("SHOPIFY_TOKEN")
    if not (store and token):
        print("Set SHOPIFY_STORE and SHOPIFY_TOKEN.")
        sys.exit(2)
    path = sys.argv[1]
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            src = row["image_url"].split("?",1)[0]
            name = row["suggested_filename"].strip()
            print(f"Uploading {name} from {src} ...", end=" ")
            url = file_create_image(store, token, name, src)
            print("OK" if url else "FAILED", url or "")

if __name__ == "__main__":
    main()

