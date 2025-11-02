# Changelog

All notable changes to the Brush On Block GEO + accessibility project are documented here.

Format loosely follows Keep‑a‑Changelog with Added/Changed/Fixed sections per date.

## 2025-10-22

### Added
- Image audits and planning
  - `audits/brushonblock-images-by-page-2025-10-22.csv`
  - `audits/brushonblock-images-unique-2025-10-22.csv`
  - `audits/brushonblock-priority-fixes-2025-10-22.csv`
  - `audits/brushonblock-rename-plan-2025-10-22.csv`
- Shopify automation & utilities
  - `scripts/crawl_bob_images.py`, `scripts/derive_page_alt_stats.py`, `scripts/crawl_bob_links.py`
  - `scripts/shopify_apply_alt_and_rename.py`, `scripts/shopify_fill_missing_product_alts.py`
  - `scripts/shopify_apply_renames.py`, `scripts/shopify_patch_theme_refs.py`, `scripts/shopify_deploy_schema.py`
- GEO schema (prepared)
  - `shopify/snippets/geo-schema.liquid` (sitewide Organization, WebSite, Breadcrumb; delegates Product/Article)
  - `shopify/snippets/schema-product.liquid` (Offer/price/availability; SKU→MPN; barcode→GTIN8/12/13/14)
  - `shopify/snippets/schema-article.liquid`
  - Back‑compat shim: `shopify/snippets/seo-schema.liquid` → renders `geo-schema`
- Robots and AI crawler policies (staging)
  - `templates/robots.txt.liquid` (explicitly allows GPTBot, Google‑Extended, Perplexity, Claude, Applebot‑Extended, CCBot, Amazonbot)
  - `docs/ai.txt`, `docs/llms.txt` for Files + redirects
- Documentation
  - `docs/executive-summary-2025-10-22.md`
  - `docs/implementation-report-2025-10-22.md`
  - `docs/progress-report-2025-10-22.md`
  - `docs/shopify-alt-filename-checklist-2025-10-22.md`
  - `docs/deploy-schema-and-robots.md`

### Changed
- Accessibility
  - Product media ALT coverage completed (101 products / 453 images). Remaining empty ALTs (143) autofilled with product title → now 0 missing.
  - Pages handled add‑only; Press Archive images brought to compliance. Blogs deferred to editorial pass.
- Staging theme setup
  - New staging theme `185693077873` created and configured.
  - Header refactor to ensure brand‑blue SVG logo renders consistently; logo width set on image to preserve 3‑column flex layout.
  - Head render updated to `{% render 'geo-schema' %}` (GEO‑first); `seo-schema` kept as a shim.
- Terminology
  - Documentation updated to use “GEO” (Generative Engine Optimization) consistently across docs.

### Fixed
- Header logo issues on previous staging copies
  - Eliminated flex collapse in header; removed zero‑dimension SVG pitfalls.
  - Resolved white‑on‑white logo by wiring the blue SVG via Files and explicit width.

### Notes / Verification
- ALT re‑audit confirms 0 missing ALTs on product media post‑fill.
- robots.txt (staging) returns custom policy and sitemap.
- GEO schema snippets prepared; deployment to staging in progress (API and/or manual). After install, validate:
  - Home: Organization + WebSite
  - PDP: Product
  - Article: Article
  - Non‑home pages: BreadcrumbList

### Next
- Complete GEO schema installation on staging (and archive legacy JSON‑LD into `snippets/legacy-schema-archive-2025-10-22.liquid`).
- Upload `ai.txt` / `llms.txt` to Files and create redirects; verify 200s.
- Begin prioritized image rename Batch 1 on staging (homepage + top products), QA visuals/links, then publish.
- Generate blog article ALT fixpacks for an editorial pass; apply add‑only.
