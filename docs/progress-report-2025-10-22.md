# Brush On Block — Progress Report (2025-10-22)

## Overview
- Goal: Improve accessibility, GEO (Generative Engine Optimization), and crawl posture; prepare assets and structure for search + LLM surfaces with minimal risk.
- Environments: Live (no theme code changes), Staging theme `185693077873` (active for testing).

## What We’ve Completed
- Accessibility (ALT)
  - Products: Audited 101 products / 453 images; filled 143 missing → 0 remaining.
  - Pages: Add‑only pass; fixed Press Archive. Blogs deferred to editorial.
- Header/logo hardening (staging)
  - Blue SVG logo wired; explicit image width set to preserve 3‑column layout.
  - Kept transparent header setting aligned or disabled (no collapse; looks consistent).
- Crawler directives (staging)
  - `templates/robots.txt.liquid` installed; explicitly allows major AI/LLM crawlers and preserves core disallows. Sitemap exposed.
- GEO schema (prepared)
  - Sitewide loader: `snippets/geo-schema.liquid` (Organization, WebSite, Breadcrumb; delegates Product/Article).
  - PDP: `snippets/schema-product.liquid` (Offer, price/currency/availability; SKU→MPN; barcode→GTIN8/12/13/14 if present).
  - Article: `snippets/schema-article.liquid` (headline, image, author, dates).
  - Backward‑compatible shim: `snippets/seo-schema.liquid` → renders `geo-schema`.
- AI text files (prepared)
  - `docs/ai.txt` and `docs/llms.txt` for Files + redirects.
- Image inventory & rename planning
  - Full crawl CSVs (by‑page and unique), priority fixes, and a rename plan with reasons/steps.

## Artifacts (this repo)
- Audits
  - `audits/brushonblock-images-by-page-2025-10-22.csv`
  - `audits/brushonblock-images-unique-2025-10-22.csv`
  - `audits/brushonblock-priority-fixes-2025-10-22.csv`
  - `audits/brushonblock-rename-plan-2025-10-22.csv`
  - `audits/shopify-product-images-missing-alt-2025-10-22.csv` (pre‑fill snapshot)
  - `audits/shopify-product-alt-fills-2025-10-22.csv` (fill log)
- Scripts
  - Crawlers/extractors: `scripts/crawl_bob_images.py`, `scripts/derive_page_alt_stats.py`, `scripts/crawl_bob_links.py` (internal‑links proxy)
  - Shopify apply/update: `scripts/shopify_apply_alt_and_rename.py`, `scripts/shopify_fill_missing_product_alts.py`, `scripts/shopify_patch_theme_refs.py`, `scripts/shopify_apply_renames.py`, `scripts/shopify_deploy_schema.py`
- Documentation
  - Executive summary: `docs/executive-summary-2025-10-22.md`
  - Implementation report: `docs/implementation-report-2025-10-22.md`
  - Checklist: `docs/shopify-alt-filename-checklist-2025-10-22.md`
  - Deploy guide: `docs/deploy-schema-and-robots.md`

## Staging Theme — Current Status (185693077873)
- Header/logo: Blue SVG in Files; `.header__logo-image { width: 215px; height:auto; }` retains 3‑column balance.
- Robots: Custom `robots.txt.liquid` is active (preview returns our policy).
- GEO schema: `render 'geo-schema'` added to `<head>`; snippets are being installed/validated.
- ai/llms: ready to upload to Files + add redirects.

## Validation Plan (staging)
- Home (Organization + WebSite): `/?preview_theme_id=185693077873`
- PDP (Product): `/products/brush-on-block-spf-30-brush-refill-set?preview_theme_id=185693077873`
- Article (Article): `/blogs/news/sunscreen-spray-that-you-can-feel-good-about?preview_theme_id=185693077873`
- BreadcrumbList: present on non‑home pages.
- AI files: `/ai.txt?preview_theme_id=185693077873`, `/llms.txt?preview_theme_id=185693077873`

## Outstanding (Near‑Term)
- [ ] Finish installing GEO snippets on staging and validate JSON‑LD (1 Product, 1 Article, sitewide Home).
- [ ] Upload `ai.txt` / `llms.txt` to Files and create URL redirects.
- [ ] Back up legacy JSON‑LD to `snippets/legacy-schema-archive-2025-10-22.liquid` and comment out originals to avoid duplicates.
- [ ] Prioritized image renames (Batch 1: homepage + top products) in staging; QA; then publish.
- [ ] Editorial blog ALT pass via per‑article fixpacks (optional but recommended).

## Risks & Mitigations
- Theme references to images are distributed across templates/sections JSON; all swaps to be staged, diffed, and QA’d before publish.
- Legacy schema duplication could dilute signals; mitigation: archive/comment legacy blocks once GEO schema is live.
- Third‑party apps may inject markup; verify schema/ALT/robots on pages with app widgets.

## Next 7 Days — Proposed Plan
- Day 1–2: Complete GEO deployment on staging; validate with Google’s Rich Results Test; archive legacy schema.
- Day 2–3: Ship ai.txt / llms.txt and confirm redirects.
- Day 3–5: Rename Batch 1 images on staging, update JSON references, QA visual + broken‑links; publish if green.
- Day 5–7: Prep editorial blog ALT fixpacks; begin review or schedule a later pass.

## Rollback / Safety
- ALT updates are reversible per image in Admin.
- Staging theme can be re‑duplicated anytime; Files uploads persist but are harmless.
- GEO schema can be disabled by removing the single `{% render 'geo-schema' %}` line; legacy schema archive provides restore points.

---
Last updated: 2025-10-22
