#!/usr/bin/env python3
import csv
import time
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from io import StringIO
from typing import Dict, List, Set, Tuple

try:
    import requests
except Exception:
    print("This script requires the 'requests' package.")
    sys.exit(1)

import xml.etree.ElementTree as ET


BASE_DOMAIN = "brushonblock.com"
BASE_URL = f"https://{BASE_DOMAIN}"
USER_AGENT = "LinkAuditBot/1.0 (+https://example.com)"
RATE_LIMIT_SEC = 0.5
TIMEOUT = 20


def http_get(url: str):
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        if r.status_code == 200:
            return r
        return None
    except Exception:
        return None


def is_same_host(url: str) -> bool:
    return BASE_DOMAIN in url.split("/")[2] if url.startswith("http") else True


def derive_page_title(html: str) -> str:
    # Prefer og:title then <title>
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: List[str] = []
        self._title_buf = StringIO()
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            d = {k.lower(): v for k, v in attrs}
            href = d.get("href")
            if href:
                self.links.append(href)
        elif tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.write(data)

    def title(self) -> str:
        return self._title_buf.getvalue().strip()


def parse_links(html: str) -> Tuple[List[str], str]:
    p = LinkParser()
    p.feed(html)
    title = derive_page_title(html) or p.title()
    return p.links, title


def gather_urls_from_sitemaps() -> List[str]:
    urls: List[str] = []
    seen_sitemaps: Set[str] = set()

    def fetch_sitemap(url: str):
        if url in seen_sitemaps:
            return
        seen_sitemaps.add(url)
        time.sleep(RATE_LIMIT_SEC)
        r = http_get(url)
        if not r:
            return
        try:
            root = ET.fromstring(r.text)
        except Exception:
            return
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in root.findall(".//sm:sitemap/sm:loc", ns):
            loc_url = loc.text.strip()
            if is_same_host(loc_url):
                fetch_sitemap(loc_url)
        for loc in root.findall(".//sm:url/sm:loc", ns):
            loc_url = loc.text.strip()
            if is_same_host(loc_url):
                urls.append(loc_url)

    fetch_sitemap(f"{BASE_URL}/sitemap.xml")
    seen: Set[str] = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def absolutize(href: str) -> str:
    if not href:
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return BASE_URL + href
    if href.startswith("http://") or href.startswith("https://"):
        return href
    # ignore mailto, tel, fragments
    return href


def canon(url: str) -> str:
    # strip query/hash
    url = url.split("#", 1)[0]
    url = url.split("?", 1)[0]
    # normalize trailing slash except the base blog path
    if url.endswith("/") and not url.rstrip("/").endswith("/blogs/news"):
        url = url.rstrip("/")
    return url


def is_blog_article(url: str) -> bool:
    if not url.startswith(BASE_URL):
        return False
    path = url[len(BASE_URL):]
    if not path.startswith("/blogs/news/"):
        return False
    if "/tagged/" in path:
        return False
    # Exclude the blog index
    if path.rstrip("/") == "/blogs/news":
        return False
    # Articles usually /blogs/news/<slug>
    parts = path.strip("/").split("/")
    return len(parts) == 3


def main():
    print("Fetching sitemap and pages…", flush=True)
    all_pages = gather_urls_from_sitemaps()
    print(f"Discovered {len(all_pages)} pages.")

    link_counts: Dict[str, int] = defaultdict(int)
    linked_from: Dict[str, Set[str]] = defaultdict(set)

    for i, page in enumerate(all_pages, 1):
        time.sleep(RATE_LIMIT_SEC)
        r = http_get(page)
        if not r:
            continue
        html = r.text
        links, _ = parse_links(html)
        for href in links:
            abs_url = absolutize(href)
            if not abs_url or not abs_url.startswith("http"):
                continue
            cu = canon(abs_url)
            if is_blog_article(cu):
                link_counts[cu] += 1
                linked_from[cu].add(page)
        if i % 25 == 0:
            print(f"Processed {i}/{len(all_pages)} pages…", flush=True)

    # Fetch titles for each blog article
    titles: Dict[str, str] = {}
    for j, url in enumerate(link_counts.keys(), 1):
        time.sleep(RATE_LIMIT_SEC)
        r = http_get(url)
        if r:
            titles[url] = derive_page_title(r.text)

    # Export CSV
    import os, datetime
    os.makedirs("audits", exist_ok=True)
    out = f"audits/blog-internal-link-leaders-{time.strftime('%Y-%m-%d')}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["blog_url", "title", "internal_link_count", "unique_pages_linking", "sample_sources"])
        for url, count in sorted(link_counts.items(), key=lambda kv: kv[1], reverse=True):
            pages = sorted(linked_from[url])
            w.writerow([url, titles.get(url, ""), count, len(pages), "; ".join(pages[:3])])

    # Print Top 10
    top10 = sorted(link_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    print("Top 10 by internal links:")
    for rank, (u, c) in enumerate(top10, 1):
        print(f"{rank}. {titles.get(u, '')} — {c} links → {u}")
    print(out)


if __name__ == "__main__":
    main()
