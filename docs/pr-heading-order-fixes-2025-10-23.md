**Title**
- Brush On Block: Fix Out‑of‑Order Headings (H1–H6)

**Summary**
- Audited 314 pages on 2025-10-22; 86 pages show heading issues (154 total).
- Common problems:
  - First heading is not H1 (often an H2 before the actual title).
  - Multiple H1s on a page (duplicate product titles/sections).
  - Skips upward in level (e.g., H1 → H3 for section headers like “Thoughtfully Chosen Ingredients” and “Reviews”).
  - Some collection pages render no H1–H6 at all.

**Artifacts**
- Findings: `docs/brushonblock-heading-order-2025-10-22.md`
- Raw data: `audits/brushonblock-heading-order-2025-10-22.json`

**Scope & Impact**
- Improves semantic structure and accessibility.
- Clarifies page topics for search engines, reducing outline ambiguities.

**Fix Plan (by template)**
- Product template (`product`)
  - Ensure the product title is the single page H1 and appears first in DOM.
  - Demote any earlier category/type labels currently using H2 (e.g., “Powder”, “Balm”, “Spray”) to text or H3/H4, and place them after the H1.
  - Standardize section headers (“Thoughtfully Chosen Ingredients”, “Reviews”, promo blocks) to `H2` when they are top‑level sections under the product title.
  - Remove/convert duplicate H1s to H2s or non‑heading tags.

- Collection template (`collection`)
  - Render collection title as `H1` near the top of the page.
  - Use `H2` for any subsections within the collection page (filters, featured blocks, editorial content).
  - Ensure cards and snippets inside the grid do not use headings that skip levels (prefer `H3` under `H2`).

- Pages template (`page`)
  - Replace current page headers (`H3`) with `H1` (About, Contact, FAQs, How to Apply, Shipping).
  - Use `H2` for primary sections under the page title.

- Blog index (`/blogs/news`)
  - Keep the page title as `H1` and render each article card title as `H2` (not `H3`).

**Liquid-Level Changes (examples)**
- Product title
  - Replace duplicate page‑level H1s with one canonical H1:
    - `<h1 class="product__title">{{ product.title }}</h1>`
  - Any earlier headings (e.g., product type/label) should be demoted:
    - `Powder`/`Balm` label: `<div class="product__type">{{ product.type }}</div>` or `<h3>` only if it truly represents a sub‑section.

- Section headers used in features/promos (often `image-with-text`)
  - Change `<h3 class="section-title">…</h3>` to `<h2 class="section-title">…</h2>` when it is a peer of other top‑level sections under the page title.

- Reviews blocks
  - Demote from `H3` to `H2` when directly under the page title, or to `H3` when nested under a `H2` section.

**Representative Issues to Fix**
- Product pages (many): first heading is `H2` like “Powder” before any H1. Then later duplicate H1s and H1 → H3 jumps (e.g., “Thoughtfully Chosen Ingredients”, “Reviews”).
- CMS pages (About/Contact/FAQs/etc.): first heading is `H3` and should be `H1`.
- Collection pages (`/collections/kids`, `/collections/sprays`): no H1–H6 present — add an `H1` for the collection title.

**Acceptance Criteria**
- Each page has exactly one `H1`, and it is the first heading in DOM order.
- No upward skips greater than one level (e.g., `H2` → `H4`).
- Collection and CMS pages render appropriate `H1` titles.
- Product page sections sit directly under the product title as `H2`s.

**Validation**
- Re‑run: `python3 scripts/audit_heading_order.py --max-pages 180 --out-prefix brushonblock-heading-order`
- Confirm the updated report shows:
  - 0 pages with `first_heading_not_h1`.
  - 0 pages with `multiple_h1`.
  - 0 pages with `skipped_level` (or acceptable residuals explained by intentional nesting).

**Notes**
- The audit is based on server‑rendered HTML. If headings are injected by JavaScript at runtime, ensure the rendered DOM also meets the criteria.
