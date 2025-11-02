#!/usr/bin/env python3
import os
import sys
import json
import requests

API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"

def create_redirect(store: str, token: str, path: str, target: str) -> int:
    url = f"{rest_base(store)}/redirects.json"
    payload = {"redirect": {"path": path, "target": target}}
    r = requests.post(url, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, json=payload, timeout=60)
    # 422 if exists; treat as success
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:200]}
    print(f"POST {path} -> {r.status_code} {body if r.status_code>=400 else ''}")
    return r.status_code

def main():
    store = os.getenv("SHOPIFY_STORE")
    token = os.getenv("SHOPIFY_TOKEN")
    ai_url = os.getenv("AI_URL")
    llms_url = os.getenv("LLMS_URL")
    if not (store and token and ai_url and llms_url):
        print("Set SHOPIFY_STORE, SHOPIFY_TOKEN, AI_URL, LLMS_URL env vars.")
        sys.exit(2)
    s1 = create_redirect(store, token, "/ai.txt", ai_url)
    s2 = create_redirect(store, token, "/llms.txt", llms_url)
    # Basic success criterion: both 201/200/202/422
    ok = all(code in (200,201,202,301,302,422) for code in (s1,s2))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()

