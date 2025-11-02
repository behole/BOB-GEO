#!/usr/bin/env python3
import csv
import glob
import os
from collections import defaultdict
from datetime import datetime


def latest_by_page_csv() -> str:
    paths = sorted(glob.glob("audits/brushonblock-images-by-page-*.csv"))
    if not paths:
        raise SystemExit("No by-page CSV found. Run crawl first.")
    return paths[-1]


def slugify_page(url: str) -> str:
    url = url.replace("https://", "").replace("http://", "")
    url = url.strip("/").replace("/", "-")
    url = url.replace("?", "_")
    if len(url) > 150:
        url = url[:150]
    return url


def main():
    src = latest_by_page_csv()
    today = datetime.now().strftime('%Y-%m-%d')
    out_pages = f"audits/brushonblock-top-pages-missing-alt-{today}.csv"
    fixpack_dir = f"audits/fixpacks-{today}"
    os.makedirs(fixpack_dir, exist_ok=True)

    pages = defaultdict(list)
    with open(src, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            pages[row['page_url']].append(row)

    summary = []
    for page_url, rows in pages.items():
        total = len(rows)
        # contentful missing ALT: curr empty AND suggested non-empty
        missing_alt_content = sum(1 for x in rows if (not x['current_alt'].strip()) and x['suggested_alt'].strip())
        # should be decorative: suggested_alt empty but current non-empty
        alt_should_be_empty = sum(1 for x in rows if x['current_alt'].strip() and (not x['suggested_alt'].strip()))
        decorative = sum(1 for x in rows if not x['suggested_alt'].strip())
        summary.append({
            'page_url': page_url,
            'total_images': total,
            'missing_alt_content': missing_alt_content,
            'alt_should_be_empty': alt_should_be_empty,
            'decorative_count': decorative,
        })

    # Sort by contentful missing ALT desc then total images desc
    summary.sort(key=lambda x: (x['missing_alt_content'], x['total_images']), reverse=True)

    with open(out_pages, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['rank', 'page_url', 'total_images', 'missing_alt_content', 'alt_should_be_empty', 'decorative_count'])
        for i, s in enumerate(summary, 1):
            w.writerow([i, s['page_url'], s['total_images'], s['missing_alt_content'], s['alt_should_be_empty'], s['decorative_count']])

    # Write fixpacks for top 25 pages
    top = summary[:25]
    for s in top:
        page_url = s['page_url']
        rows = pages[page_url]
        slug = slugify_page(page_url)
        out = os.path.join(fixpack_dir, f"{slug}.csv")
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['page_url', 'image_url', 'current_filename', 'current_alt', 'suggested_alt', 'suggested_filename'])
            for r in rows:
                w.writerow([r['page_url'], r['image_url'], r['current_filename'], r['current_alt'], r['suggested_alt'], r['suggested_filename']])

    print(out_pages)
    print(fixpack_dir)


if __name__ == '__main__':
    main()

