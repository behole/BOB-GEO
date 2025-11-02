#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from io import StringIO
from typing import Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:
    print("This script requires the 'requests' package.")
    sys.exit(1)


BASE_DOMAIN = "brushonblock.com"
BASE_URL = f"https://{BASE_DOMAIN}"
USER_AGENT = "HeadingAuditBot/1.0 (+https://example.com)"
RATE_LIMIT_SEC = 0.5
TIMEOUT = 20


def http_get(url: str):
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        if r.status_code == 200 and "text/html" in r.headers.get("content-type", "").lower():
            return r
        return None
    except Exception:
        return None


def is_same_host(url: str) -> bool:
    return BASE_DOMAIN in url.split("/")[2] if url.startswith("http") else True


def gather_urls_from_sitemaps(sitemap_url: str) -> List[str]:
    urls: List[str] = []
    seen_sitemaps = set()

    def fetch_sitemap(url: str):
        if url in seen_sitemaps:
            return
        seen_sitemaps.add(url)
        time.sleep(RATE_LIMIT_SEC)
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        except Exception:
            return
        if not r or r.status_code != 200:
            return
        try:
            root = ET.fromstring(r.text)
        except Exception:
            return
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        # recurse into sitemap index
        for loc in root.findall(".//sm:sitemap/sm:loc", ns):
            loc_url = (loc.text or "").strip()
            if loc_url and is_same_host(loc_url):
                fetch_sitemap(loc_url)
        # collect urlset urls
        for loc in root.findall(".//sm:url/sm:loc", ns):
            loc_url = (loc.text or "").strip()
            if loc_url and is_same_host(loc_url):
                urls.append(loc_url)

    fetch_sitemap(sitemap_url)
    # de-dupe while preserving order
    seen = set()
    out: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def categorize(url: str) -> str:
    if not url.startswith("http"):
        return "other"
    try:
        path = url.split("/", 3)[3]
    except Exception:
        path = ""
    path = "/" + path
    if path in ("/", ""):
        return "home"
    if path.startswith("/products/"):
        return "products"
    if path.startswith("/collections/"):
        return "collections"
    if path.startswith("/blogs/"):
        return "blogs"
    if path.startswith("/pages/"):
        return "pages"
    return "other"


HEADING_TAGS = {f"h{i}": i for i in range(1, 7)}


@dataclass
class Heading:
    level: int
    text: str
    path: str
    attrs: Dict[str, str]


class HeadingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack: List[str] = []
        self.headings: List[Heading] = []
        self._in_heading: Optional[Tuple[str, int, Dict[str, str], StringIO]] = None

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        self.stack.append(t)
        if t in HEADING_TAGS and self._in_heading is None:
            attrs_dict = {k.lower(): v for k, v in attrs}
            buf = StringIO()
            level = HEADING_TAGS[t]
            self._in_heading = (t, level, attrs_dict, buf)

    def handle_endtag(self, tag):
        t = tag.lower()
        if self._in_heading and t == self._in_heading[0]:
            tag_name, level, attrs_dict, buf = self._in_heading
            # build a simple path snapshot (last few ancestors)
            ancestry = [x for x in self.stack if x != tag_name]
            path = ">".join(ancestry[-6:] + [tag_name])
            text = re.sub(r"\s+", " ", buf.getvalue()).strip()
            self.headings.append(Heading(level=level, text=text, path=path, attrs=attrs_dict))
            self._in_heading = None
        if self.stack:
            # pop until matching tag (be defensive)
            try:
                idx = len(self.stack) - 1 - self.stack[::-1].index(t)
                self.stack = self.stack[:idx]
            except ValueError:
                # tag not found; reset stack when malformed
                self.stack = []

    def handle_data(self, data):
        if self._in_heading is not None:
            self._in_heading[3].write(data)


def analyze_headings(headings: List[Heading]) -> Dict:
    issues: List[Dict] = []
    levels = [h.level for h in headings]
    if not headings:
        return {"sequence": levels, "issues": [{"type": "no_headings", "message": "No H1–H6 tags found"}]}
    # First heading should be H1
    if headings[0].level != 1:
        issues.append({
            "type": "first_heading_not_h1",
            "message": f"First heading is H{headings[0].level} not H1",
            "curr_level": headings[0].level,
            "curr_text": headings[0].text,
            "curr_path": headings[0].path,
        })
    # Multiple H1s
    h1_count = sum(1 for h in headings if h.level == 1)
    if h1_count > 1:
        issues.append({
            "type": "multiple_h1",
            "message": f"Found {h1_count} H1 tags",
            "count": h1_count,
        })
    # Jumps upward by more than 1 level
    prev = headings[0]
    for h in headings[1:]:
        if h.level > prev.level + 1:
            issues.append({
                "type": "skipped_level",
                "message": f"Jump from H{prev.level} to H{h.level}",
                "prev_level": prev.level,
                "prev_text": prev.text,
                "curr_level": h.level,
                "curr_text": h.text,
                "curr_path": h.path,
            })
        prev = h
    return {"sequence": levels, "issues": issues}


def audit_page(url: str) -> Dict:
    time.sleep(RATE_LIMIT_SEC)
    r = http_get(url)
    if not r:
        return {"url": url, "error": "fetch_failed"}
    parser = HeadingParser()
    try:
        parser.feed(r.text)
    except Exception:
        return {"url": url, "error": "parse_failed"}
    analysis = analyze_headings(parser.headings)
    return {
        "url": url,
        "headings": [asdict(h) for h in parser.headings],
        **analysis,
    }


def pick_sample(urls: List[str], max_pages: int) -> List[str]:
    buckets: Dict[str, List[str]] = defaultdict(list)
    for u in urls:
        if not u.startswith("http"):
            continue
        if any(u.endswith(ext) for ext in (".xml", ".txt", ".jpg", ".png", ".webp", ".svg")):
            continue
        buckets[categorize(u)].append(u)
    # ensure homepage first if present
    sample: List[str] = []
    for cat in ("home", "products", "collections", "blogs", "pages", "other"):
        for u in buckets.get(cat, [])[: max(1, max_pages // 6)]:
            sample.append(u)
            if len(sample) >= max_pages:
                return sample
    return sample


def render_markdown(audits: List[Dict], scanned_count: int) -> str:
    date = time.strftime("%Y-%m-%d")
    pages_with_issues = [a for a in audits if a.get("issues")]
    total_issues = sum(len(a.get("issues", [])) for a in audits)
    by_type = Counter(i["type"] for a in audits for i in a.get("issues", []))

    def bullet_issue(i: Dict) -> str:
        t = i["type"]
        if t == "skipped_level":
            return f"- Jump from H{i['prev_level']} to H{i['curr_level']} at “{i['curr_text'][:80]}”. Path: `{i['curr_path']}`"
        if t == "first_heading_not_h1":
            return f"- First heading is H{i['curr_level']} (“{i['curr_text'][:80]}”), expected H1. Path: `{i['curr_path']}`"
        if t == "multiple_h1":
            return f"- Multiple H1 tags found ({i['count']})."
        if t == "no_headings":
            return f"- No H1–H6 tags found on page."
        return f"- {t}"

    lines: List[str] = []
    lines.append(f"## Brush On Block — Heading Order Audit ({date})")
    lines.append("")
    lines.append("Summary")
    lines.append("")
    lines.append(f"- Pages scanned: {scanned_count}")
    lines.append(f"- Pages with issues: {len(pages_with_issues)}")
    lines.append(f"- Total issues found: {total_issues}")
    if by_type:
        lines.append("- Issue breakdown:")
        for k, v in sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  - {k}: {v}")
    lines.append("")
    lines.append("Guidance")
    lines.append("")
    lines.append("- Start each page with a single H1.")
    lines.append("- Do not increase heading levels by more than one at a time (H2 → H3 is OK; H2 → H4 is not).")
    lines.append("- You may decrease heading levels freely when closing a section (e.g., H4 → H2).")
    lines.append("")
    lines.append("Details by Page")
    lines.append("")
    for a in audits:
        if not a.get("issues"):
            continue
        url = a["url"]
        lines.append(f"### {url}")
        for i in a["issues"][:12]:  # cap per page for readability
            lines.append(bullet_issue(i))
        lines.append("")
    lines.append("")
    lines.append("Validation")
    lines.append("")
    lines.append("- Generated by `scripts/audit_heading_order.py` using the site sitemap.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Audit heading order (H1–H6) across pages.")
    ap.add_argument("--sitemap", default=f"{BASE_URL}/sitemap.xml")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--out-prefix", default="brushonblock-heading-order")
    args = ap.parse_args()

    print("Discovering pages from sitemap…", flush=True)
    urls = gather_urls_from_sitemaps(args.sitemap)
    if not urls:
        print("No URLs discovered.")
        sys.exit(2)

    sample = pick_sample(urls, args.max_pages)
    print(f"Scanning {len(sample)} pages (from {len(urls)} discovered)…", flush=True)

    audits: List[Dict] = []
    for idx, url in enumerate(sample, 1):
        audits.append(audit_page(url))
        if idx % 25 == 0:
            print(f"\tProcessed {idx}/{len(sample)}…", flush=True)

    os.makedirs("audits", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    date = time.strftime("%Y-%m-%d")
    json_path = os.path.join("audits", f"{args.out_prefix}-{date}.json")
    md_path = os.path.join("docs", f"{args.out_prefix}-{date}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"scanned": len(sample), "results": audits}, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(audits, scanned_count=len(sample)))

    print("\nSaved:")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()

