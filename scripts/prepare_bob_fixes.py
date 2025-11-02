#!/usr/bin/env python3
import csv
import os
import re
import glob
from datetime import datetime


def latest_unique_csv() -> str:
    paths = sorted(glob.glob("audits/brushonblock-images-unique-*.csv"))
    if not paths:
        raise SystemExit("No unique images CSV found. Run crawl first.")
    return paths[-1]


def classify_scope(pages: list[str]) -> str:
    # Choose the most specific scope by precedence
    has_home = any(p.rstrip('/') == 'https://brushonblock.com' or p.rstrip('/') == 'https://brushonblock.com/' for p in pages)
    has_prod = any('/products/' in p for p in pages)
    has_coll = any('/collections/' in p for p in pages)
    has_blog = any('/blogs/' in p for p in pages)
    has_page = any('/pages/' in p for p in pages)
    if has_home:
        return 'homepage'
    if has_prod:
        return 'product'
    if has_coll:
        return 'collection'
    if has_blog:
        return 'blog'
    if has_page:
        return 'page'
    return 'theme/global'


def has_uppercase(name: str) -> bool:
    return any(c.isupper() for c in name)


def has_underscores(name: str) -> bool:
    return '_' in name


def is_generic_name(name: str) -> bool:
    base = os.path.splitext(os.path.basename(name))[0].lower()
    return bool(re.search(r'^(img|image|picture|photo)[-_]?\d+', base) or re.search(r'image[-_]?\d+', base))


def priority_score(pages: list[str], scope: str, best_alt: str, suggested_alt: str, filename: str) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    pages_count = len(pages)
    if any(p.rstrip('/') in ('https://brushonblock.com', 'https://brushonblock.com/') for p in pages):
        score += 100; reasons.append('homepage')
    if pages_count > 25:
        score += 60; reasons.append('sitewide component')
    elif pages_count > 10:
        score += 40; reasons.append('reused many pages')
    elif pages_count > 3:
        score += 15; reasons.append('reused multiple pages')

    scope_weights = {
        'product': 30,
        'blog': 20,
        'collection': 18,
        'page': 12,
        'homepage': 50,
        'theme/global': 25,
    }
    if scope in scope_weights:
        score += scope_weights[scope]

    if not best_alt.strip() and suggested_alt.strip():
        score += 60; reasons.append('missing ALT')
    if best_alt.strip() and not suggested_alt.strip():
        # Likely decorative but currently has alt -> fix to empty
        score += 35; reasons.append('decorative should be empty')

    if has_uppercase(filename):
        score += 8; reasons.append('uppercase in name')
    if has_underscores(filename):
        score += 8; reasons.append('underscores in name')
    if is_generic_name(filename):
        score += 10; reasons.append('generic filename')

    return score, reasons


def decide_action(scope: str, best_alt: str, suggested_alt: str, decorative: bool) -> str:
    # ALT guidance first
    if decorative:
        return "Ensure alt=\"\" (decorative). No rename needed."
    if not best_alt.strip() and suggested_alt.strip():
        return "Add descriptive ALT on all uses."
    # Filename guidance by scope
    if scope in ('product', 'collection', 'blog', 'page', 'homepage'):
        return "Optional: re-upload with GEO filename; update content references."
    return "Optional: rename theme asset and update theme references."


def main():
    src = latest_unique_csv()
    today = datetime.now().strftime('%Y-%m-%d')
    out_priority = f"audits/brushonblock-priority-fixes-{today}.csv"
    out_rename = f"audits/brushonblock-rename-plan-{today}.csv"

    rows = []
    with open(src, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            pages = [p.strip() for p in row['pages_found_on'].split(';') if p.strip()]
            scope = classify_scope(pages)
            decorative = (row['suggested_alt'].strip() == '')
            score, reasons = priority_score(pages, scope, row['best_current_alt'], row['suggested_alt'], row['current_filename'])
            rows.append({
                'image_url': row['image_url'],
                'current_filename': row['current_filename'],
                'suggested_filename': row['suggested_filename'],
                'pages': pages,
                'pages_count': len(pages),
                'best_current_alt': row['best_current_alt'],
                'suggested_alt': row['suggested_alt'],
                'scope': scope,
                'decorative': decorative,
                'score': score,
                'reasons': ", ".join(reasons),
            })

    # Sort descending by score, then by pages_count
    rows.sort(key=lambda x: (x['score'], x['pages_count']), reverse=True)

    # Write priority fixes CSV (top 250 to keep manageable)
    with open(out_priority, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['rank', 'image_url', 'current_filename', 'suggested_filename', 'pages_count', 'pages_sample', 'scope', 'decorative', 'best_current_alt', 'suggested_alt', 'priority_reasons', 'recommended_action'])
        for idx, r in enumerate(rows[:250], 1):
            pages_sample = "; ".join(r['pages'][:3])
            action = decide_action(r['scope'], r['best_current_alt'], r['suggested_alt'], r['decorative'])
            w.writerow([idx, r['image_url'], r['current_filename'], r['suggested_filename'], r['pages_count'], pages_sample, r['scope'], 'yes' if r['decorative'] else 'no', r['best_current_alt'], r['suggested_alt'], r['reasons'], action])

    # Write rename plan CSV (all candidates with filename hygiene issues)
    with open(out_rename, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['image_url', 'current_filename', 'suggested_filename', 'scope', 'reason_for_rename', 'recommended_steps', 'pages_count', 'pages_sample'])
        for r in rows:
            bad_name = has_uppercase(r['current_filename']) or has_underscores(r['current_filename']) or is_generic_name(r['current_filename'])
            if not bad_name:
                continue
            if r['scope'] in ('product', 'collection', 'blog', 'page', 'homepage'):
                steps = 'Re-upload media with suggested filename; update content references (product media or rich text).'
            else:
                steps = 'Rename theme asset and update references in theme code (sections/snippets/assets).'
            reason = []
            if has_uppercase(r['current_filename']): reason.append('uppercase')
            if has_underscores(r['current_filename']): reason.append('underscores')
            if is_generic_name(r['current_filename']): reason.append('generic')
            pages_sample = "; ".join(r['pages'][:3])
            w.writerow([r['image_url'], r['current_filename'], r['suggested_filename'], r['scope'], ", ".join(reason), steps, r['pages_count'], pages_sample])

    print(out_priority)
    print(out_rename)


if __name__ == '__main__':
    main()
