#!/usr/bin/env python3
import csv
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
import html as htmllib
from io import StringIO
from typing import Dict, List, Optional, Set, Tuple

try:
    import requests
except Exception:
    print("This script requires the 'requests' package.")
    sys.exit(1)

import xml.etree.ElementTree as ET


BASE_DOMAIN = "brushonblock.com"
BASE_URL = f"https://{BASE_DOMAIN}"
USER_AGENT = "ImageAuditBot/1.0 (+https://example.com)"
RATE_LIMIT_SEC = 0.5  # 2 req/sec
TIMEOUT = 20


def http_get(url: str) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        if r.status_code == 200:
            return r
        return None
    except Exception:
        return None


def is_same_host(url: str) -> bool:
    return BASE_DOMAIN in url.split("/")[2] if url.startswith("http") else True


def canonicalize_image_url(url: str) -> str:
    # Remove query params like ?v=...&width=... and trailing slashes
    if "?" in url:
        url = url.split("?", 1)[0]
    return url


def filename_from_url(url: str) -> str:
    url = canonicalize_image_url(url)
    return url.rstrip("/").split("/")[-1]


def ext_from_filename(name: str) -> str:
    m = re.search(r"\.([a-zA-Z0-9]+)$", name)
    return f".{m.group(1).lower()}" if m else ""


def slugify(text: str, max_words: int = 12) -> str:
    text = re.sub(r"[\s_]+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
    words = [w.lower() for w in text.strip().split() if w]
    if max_words:
        words = words[:max_words]
    return "-".join(words)


def derive_page_title(html: str) -> str:
    # Prefer og:title -> <title>
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return htmllib.unescape(m.group(1).strip())
    m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if m:
        return htmllib.unescape(re.sub(r"\s+", " ", m.group(1)).strip())
    return ""


def guess_is_product_page(url: str) -> bool:
    return "/products/" in url


def guess_is_decorative(filename: str, alt: str) -> bool:
    fname = filename.lower()
    if alt.strip() == "":
        # Empty alt often means decorative
        return True
    decorative_keys = ["icon", "sprite", "spacer", "star", "rating", "arrow", "caret", "chevron", "close", "minus", "plus"]
    if any(k in fname for k in decorative_keys):
        return True
    if fname.endswith(".svg") and ("logo" not in fname):
        # most inline SVG UI elements are decorative
        return True
    return False


def suggest_alt(alt: str, page_title: str, filename: str, page_url: str) -> str:
    if guess_is_decorative(filename, alt):
        return ""
    if alt and len(alt.strip()) >= 6:
        # keep sensible existing alt
        return alt.strip()
    # Special cases
    fname = filename.lower()
    if "logo" in fname:
        return "Brush On Block logo"
    # Product-oriented default
    base = page_title.strip() or "Brush On Block"
    # Trim branding duplication
    base = re.sub(r"\b\s*\|\s*Brush On Block\b", "", base, flags=re.I)
    base = re.sub(r"\bBrush On Block\b\s*\|\s*", "", base, flags=re.I)
    base = base.strip()
    if guess_is_product_page(page_url):
        return f"{base} product image"
    return base if base else "Brush On Block image"


def suggest_filename(current_filename: str, alt: str, page_title: str, page_url: str) -> str:
    ext = ext_from_filename(current_filename) or ".jpg"
    # Prefer alt text for filenames; fallback to product/page title; prefix brand
    basis = alt.strip() if alt.strip() else page_title.strip()
    # Remove the brand if already present to avoid duplication
    basis = re.sub(r"\bBrush On Block\b", "", basis, flags=re.I).strip()
    if not basis:
        # Last-resort: use segments from URL path
        path_seg = page_url.rstrip("/").split("/")[-1]
        basis = path_seg.replace("-", " ")
    slug = slugify(f"brush on block {basis}")
    # Avoid empty slug
    if not slug:
        slug = slugify("brush on block image")
    return f"{slug}{ext}"


@dataclass
class ImgRecord:
    page_url: str
    image_url: str
    current_filename: str
    current_alt: str
    page_title: str


class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images: List[Tuple[str, str]] = []  # (src, alt)
        self._in_title = False
        self._title_buf = StringIO()

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "img":
            d = {k.lower(): v for k, v in attrs}
            src = d.get("src") or d.get("data-src") or d.get("data-srcset") or ""
            # If srcset provided and src empty, take first URL
            if (not src) and "srcset" in d:
                srcset = d.get("srcset", "")
                if srcset:
                    src = srcset.split(",")[0].strip().split(" ")[0]
            alt = d.get("alt", "") or ""
            if src:
                self.images.append((src, alt))
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


def parse_images_from_html(html: str) -> Tuple[List[Tuple[str, str]], str]:
    parser = ImgParser()
    parser.feed(html)
    # Prefer og:title if available
    title = derive_page_title(html) or parser.title()
    return parser.images, title


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
        # If it's an index of sitemaps
        for loc in root.findall(".//sm:sitemap/sm:loc", ns):
            loc_url = loc.text.strip()
            if is_same_host(loc_url):
                fetch_sitemap(loc_url)
        # If it's a urlset
        for loc in root.findall(".//sm:url/sm:loc", ns):
            loc_url = loc.text.strip()
            if is_same_host(loc_url):
                urls.append(loc_url)

    # Start
    fetch_sitemap(f"{BASE_URL}/sitemap.xml")
    # Deduplicate, keep stable order
    seen: Set[str] = set()
    ordered = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def check_robots() -> bool:
    r = http_get(f"{BASE_URL}/robots.txt")
    if not r:
        return True
    text = r.text
    # crude: if Disallow: / for user-agent *
    blocks_all = False
    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("user-agent:"):
            current = line.split(":", 1)[1].strip()
        if line.lower().startswith("disallow:") and (current == "*"):
            path = line.split(":", 1)[1].strip()
            if path == "/":
                blocks_all = True
    return not blocks_all


def main():
    ok = check_robots()
    if not ok:
        print("robots.txt disallows crawling. Exiting.")
        sys.exit(2)

    print("Fetching sitemaps…", flush=True)
    all_urls = gather_urls_from_sitemaps()
    print(f"Discovered {len(all_urls)} pages.")

    records: List[ImgRecord] = []
    for i, page in enumerate(all_urls, 1):
        time.sleep(RATE_LIMIT_SEC)
        r = http_get(page)
        if not r:
            continue
        html = r.text
        imgs, title = parse_images_from_html(html)
        for src, alt in imgs:
            # Resolve relative URLs
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = BASE_URL + src
            rec = ImgRecord(
                page_url=page,
                image_url=src,
                current_filename=filename_from_url(src),
                current_alt=(alt or "").strip(),
                page_title=title or "",
            )
            records.append(rec)
        if i % 25 == 0:
            print(f"Processed {i}/{len(all_urls)} pages…", flush=True)

    # Write by-page CSV
    out_by_page = f"audits/brushonblock-images-by-page-{time.strftime('%Y-%m-%d')}.csv"
    out_unique = f"audits/brushonblock-images-unique-{time.strftime('%Y-%m-%d')}.csv"

    os_pages: Dict[str, List[ImgRecord]] = defaultdict(list)
    for r in records:
        os_pages[r.page_url].append(r)

    # Dedupe images by canonical URL
    by_image: Dict[str, Dict] = {}
    for r in records:
        canon = canonicalize_image_url(r.image_url)
        if canon not in by_image:
            by_image[canon] = {
                "image_url": canon,
                "current_filename": r.current_filename,
                "pages": set(),
                "alts": set(),
                "page_titles": set(),
            }
        by_image[canon]["pages"].add(r.page_url)
        if r.current_alt:
            by_image[canon]["alts"].add(r.current_alt)
        if r.page_title:
            by_image[canon]["page_titles"].add(r.page_title)

    # Ensure audits folder exists
    import os
    os.makedirs("audits", exist_ok=True)

    with open(out_by_page, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["page_url", "image_url", "current_filename", "suggested_filename", "current_alt", "suggested_alt"]) 
        for r in records:
            s_alt = suggest_alt(r.current_alt, r.page_title, r.current_filename, r.page_url)
            s_name = suggest_filename(r.current_filename, s_alt or r.current_alt, r.page_title, r.page_url)
            w.writerow([r.page_url, r.image_url, r.current_filename, s_name, r.current_alt, s_alt])

    with open(out_unique, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["image_url", "current_filename", "pages_found_on", "best_current_alt", "suggested_filename", "suggested_alt"]) 
        for canon, info in sorted(by_image.items()):
            pages = sorted(info["pages"]) 
            best_alt = sorted(info["alts"], key=lambda s: (-len(s), s))[0] if info["alts"] else ""
            # Heuristic page title for suggestion
            page_title = sorted(info["page_titles"], key=lambda s: (-len(s), s))[0] if info["page_titles"] else ""
            s_alt = suggest_alt(best_alt, page_title, info["current_filename"], pages[0] if pages else BASE_URL)
            s_name = suggest_filename(info["current_filename"], s_alt or best_alt, page_title, pages[0] if pages else BASE_URL)
            w.writerow([canon, info["current_filename"], "; ".join(pages), best_alt, s_name, s_alt])

    print("Done.")
    print(out_by_page)
    print(out_unique)


if __name__ == "__main__":
    main()
