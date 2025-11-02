#!/usr/bin/env python3
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests


API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")


def rest_base(store: str) -> str:
    return f"https://{store}.myshopify.com/admin/api/{API_VERSION}"


def rest_get(store: str, token: str, path: str, params: Optional[dict] = None) -> dict:
    url = f"{rest_base(store)}{path}"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token}, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def rest_put_asset(store: str, token: str, theme_id: str, key: str, value: str):
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    payload = {"asset": {"key": key, "value": value}}
    r = requests.put(url, json=payload, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, timeout=60)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        print("Asset upload failed:", key, r.status_code, body)
    r.raise_for_status()


def rest_get_asset(store: str, token: str, theme_id: str, key: str) -> str:
    url = f"{rest_base(store)}/themes/{theme_id}/assets.json"
    r = requests.get(url, params={"asset[key]": key}, headers={"X-Shopify-Access-Token": token}, timeout=60)
    r.raise_for_status()
    return r.json().get("asset", {}).get("value", "")


def add_render_to_head(html: str) -> str:
    # Avoid duplicate inserts: detect either geo-schema or legacy seo-schema shim
    if (
        "render 'geo-schema'" in html
        or 'render "geo-schema"' in html
        or "render 'seo-schema'" in html
        or 'render "seo-schema"' in html
    ):
        return html
    insert = "{% render 'geo-schema' %}"
    # Insert before </head>
    new = re.sub(r"</head>", insert + "\n</head>", html, count=1, flags=re.I)
    if new == html:
        return insert + "\n" + html
    return new


def graphql(store: str, token: str, query: str, variables: dict) -> dict:
    url = f"{rest_base(store)}/graphql.json"
    r = requests.post(url, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, json={"query": query, "variables": variables}, timeout=60)
    r.raise_for_status()
    return r.json()


def file_create_text(store: str, token: str, filename: str, content: str) -> Optional[str]:
    # Try GraphQL fileCreate with a data URL
    data_url = "data:text/plain;base64," + base64.b64encode(content.encode("utf-8")).decode("ascii")
    q = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files { __typename ... on MediaImage { id image { url } } ... on GenericFile { id url } }
        userErrors { field message }
      }
    }
    """
    vars = {"files": [{"filename": filename, "contentType": "TEXT", "originalSource": data_url}]}
    j = graphql(store, token, q, vars)
    # Resolve URL
    try:
        files = j["data"]["fileCreate"]["files"]
    except Exception:
        return None
    if not files:
        return None
    f = files[0]
    if f["__typename"] == "GenericFile" and f.get("url"):
        return f["url"]
    if f["__typename"] == "MediaImage":
        # Not expected for text, but handle
        rid = f.get("id")
        if rid:
            q2 = """
            query($id: ID!) { node(id: $id) { __typename ... on MediaImage { image { url } } } }
            """
            j2 = graphql(store, token, q2, {"id": rid})
            try:
                return j2["data"]["node"]["image"]["url"]
            except Exception:
                return None
    return None


def create_redirect(store: str, token: str, path: str, target: str):
    url = f"{rest_base(store)}/redirects.json"
    payload = {"redirect": {"path": path, "target": target}}
    r = requests.post(url, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, json=payload, timeout=60)
    # 422 if exists; ignore
    if r.status_code not in (200, 201, 202):
        try:
            j = r.json()
            if r.status_code == 422:
                return
        except Exception:
            pass
        r.raise_for_status()


def main():
    store = os.getenv("SHOPIFY_STORE")
    token = os.getenv("SHOPIFY_TOKEN")
    theme_id = os.getenv("SHOPIFY_THEME_ID") or (len(sys.argv) > 1 and sys.argv[1])
    if not (store and token and theme_id):
        print("Set SHOPIFY_STORE, SHOPIFY_TOKEN and provide THEME_ID (env SHOPIFY_THEME_ID or argv).")
        sys.exit(2)

    repo = Path(__file__).resolve().parents[1]
    # Push snippets
    files = {
        f"snippets/geo-schema.liquid": (repo / "shopify/snippets/geo-schema.liquid").read_text(encoding="utf-8"),
        f"snippets/seo-schema.liquid": (repo / "shopify/snippets/seo-schema.liquid").read_text(encoding="utf-8"),
        f"snippets/schema-product.liquid": (repo / "shopify/snippets/schema-product.liquid").read_text(encoding="utf-8"),
        f"snippets/schema-article.liquid": (repo / "shopify/snippets/schema-article.liquid").read_text(encoding="utf-8"),
        f"templates/robots.txt.liquid": (repo / "shopify/robots.txt.liquid").read_text(encoding="utf-8"),
    }
    for key, val in files.items():
        rest_put_asset(store, token, theme_id, key, val)
        print("Uploaded", key)

    # Insert render into theme.liquid
    theme_liq = rest_get_asset(store, token, theme_id, "layout/theme.liquid")
    new_liq = add_render_to_head(theme_liq)
    if new_liq != theme_liq:
        rest_put_asset(store, token, theme_id, "layout/theme.liquid", new_liq)
        print("Updated layout/theme.liquid with GEO schema render")
    else:
        print("theme.liquid already includes schema render")

    # Upload ai.txt and llms.txt via Files (GraphQL) and create redirects
    ai_txt = (repo / "docs/ai.txt").read_text(encoding="utf-8")
    llms_txt = (repo / "docs/llms.txt").read_text(encoding="utf-8")
    ai_url = file_create_text(store, token, "ai.txt", ai_txt)
    llms_url = file_create_text(store, token, "llms.txt", llms_txt)
    if ai_url:
        create_redirect(store, token, "/ai.txt", ai_url)
        print("Redirect /ai.txt ->", ai_url)
    else:
        print("Could not create ai.txt via Files; you can upload manually.")
    if llms_url:
        create_redirect(store, token, "/llms.txt", llms_url)
        print("Redirect /llms.txt ->", llms_url)
    else:
        print("Could not create llms.txt via Files; you can upload manually.")

    # Basic verification URLs
    origin = f"https://{store}.com" if store.endswith(".com") else f"https://{store}.myshopify.com"
    print("Verification targets:")
    print(f"  robots: https://brushonblock.com/robots.txt?preview_theme_id={theme_id}")
    print(f"  home:   https://brushonblock.com/?preview_theme_id={theme_id}")
    print(f"  ai.txt:   https://brushonblock.com/ai.txt?preview_theme_id={theme_id}")
    print(f"  llms.txt: https://brushonblock.com/llms.txt?preview_theme_id={theme_id}")


if __name__ == "__main__":
    main()
