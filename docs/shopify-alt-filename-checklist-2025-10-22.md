# Brush On Block — Shopify Image ALT + Filename Checklist (2025-10-22)

## What to ship first

- Fix ALT text on homepage and high‑traffic templates using `audits/brushonblock-priority-fixes-2025-10-22.csv` (top 250 ranked).
- Ensure decorative UI (stars, arrows, icons) use empty alt (`alt=""`).
- For product pages with missing ALT, add concise, descriptive alt to the main product media first.
- Defer renames until ALT fixes are done (renames require re‑upload and link updates).

## ALT text rules

- Be specific and concise: what/variant + action/context (≈5–12 words).
- Avoid stuffing product names repeatedly; reflect page context.
- Decorative visuals: use `alt=""`.
- Logos: `Brush On Block logo` unless the image links home (then `alt=""`).

## Where to edit ALT in Shopify

- Products: `Admin → Products → [Product] → Media → Click image → Add alt text`.
- Product description images: in the rich text editor, click image → `Edit image alt text`.
- Blog posts: `Admin → Online Store → Blog posts → [Post] → Click image → Edit image alt text`.
- Pages: `Admin → Online Store → Pages → [Page] → Click image → Edit image alt text`.
- Theme sections/snippets: `Admin → Online Store → Themes → Edit code` and ensure Liquid outputs use an `alt` value. For decorative icons, set `alt=""` or `role="presentation"`.
- Files referenced in content: replace image in the editor to set alt; the Files library itself does not carry end‑user alt.

## Filename guidance (optional but recommended)

- Lowercase, hyphenated, no spaces/underscores; keep 4–8 keywords max.
- Include brand + product/variant or clear context: `brush-on-block-spf-50-lifestyle-beach.jpg`.
- Renaming Shopify CDN images requires re‑upload; plan batch changes using the rename plan CSV.

## How to use the CSVs we shipped

- Priority fixes: `audits/brushonblock-priority-fixes-2025-10-22.csv`
  - Columns: rank, scope, pages_count, suggested_alt, recommended_action.
  - Work top‑down; start with homepage and sitewide components.
- Rename plan: `audits/brushonblock-rename-plan-2025-10-22.csv`
  - Columns: current vs suggested filename, scope, reason, steps.
  - Group by scope; re‑upload/replace accordingly.

## Implementation tips

- Keep a simple tracking sheet: page → image → status (ALT, rename, verified).
- After edits, re‑load pages and validate `alt` via browser DevTools or a11y checker.
- For theme icons and decorative SVGs, prefer inline SVG with `aria-hidden="true"` and no `alt`.

## Done criteria

- No contentful images missing ALT across homepage, product, collections, pages, and blogs.
- Decorative images have `alt=""`.
- Filenames normalized for key evergreen assets (product media, hero images, blog featured images).

