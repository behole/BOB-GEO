# Implementation Report — Brush On Block (Concise)

## Scope
- Site: brushonblock.com (Shopify).
- Live changes: Product image ALT text.
- Staging changes: Theme `185693077873` (logo display, robots; schema queued).
- Exclusions: Blog article ALT (editorial pass later). Live theme code untouched.

## Accessibility (ALT)
- Products
  - Audited 101 products / 453 images; previously 143 missing ALT.
  - Updated all missing using clean, product‑title based ALT; re‑audit confirms 0 remaining.
  - Result: Better screen‑reader compatibility and basic GEO signals store‑wide.
- Pages
  - “Add‑only” pass (no overwrites). Fixed Press Archive; no other pages required changes.
- Blogs
  - Deferred to editorial fixpacks to keep tone and context accurate.

## GEO Filenames & Renames
- Delivered
  - Unique + by‑page image inventories (CSV).
  - Priority fixes (top 250) and a rename plan (745 rows) with reasons and steps.
- Execution plan
  - Run in staging first (uploads → reference swaps → QA), then publish.
  - Paused on the new staging to avoid duplicating prior work until schema deploy is complete.

## Staging Theme & Logo
- New staging: `185693077873`.
- Outcome
  - Blue logo from Files set; explicit image width applied to `.header__logo-image` to preserve 3‑column flex layout.
  - Transparent header setting aligned to the same blue file or disabled.
- Rationale
  - Avoids SVG intrinsic‑size pitfalls and header flex collapse; keeps layout predictable.

## Crawler Directives (Robots/AI)
- Installed on staging: `templates/robots.txt.liquid`.
- Policy
  - `User-agent: *` with `Allow: /`.
  - Explicit Allow for GPTBot, Google‑Extended, PerplexityBot, ClaudeBot, Applebot‑Extended, CCBot, Amazonbot.
  - Preserves core Disallow (admin, cart, checkout, account) and includes Sitemap link.
- Value
  - Clear crawl posture for both traditional search and LLM/AI crawlers.

## Structured Data (JSON‑LD)
- Prepared snippets (ready to deploy)
  - `snippets/seo-schema.liquid`: Organization + WebSite + Breadcrumb.
  - `snippets/schema-product.liquid`: Product with Offer (currency/price/availability), Brand, MPN (SKU), GTIN (from barcode when present).
  - `snippets/schema-article.liquid`: Article with headline, dates, author, image.
- Integration
  - Add `{% render 'seo-schema' %}` inside `<head>` of `layout/theme.liquid`.
  - Product/Article schema renders only on relevant templates.
- Status
  - API deployment to staging queued; manual copy/paste fallback documented in `docs/deploy-schema-and-robots.md`.
- Value
  - Rich‑result eligibility (Products/Articles), stronger entity grounding for search and LLMs.

## AI Text Files
- ai.txt / llms.txt
  - “Allow all” policy text prepared; recommend upload to Files and URL redirects (`/ai.txt`, `/llms.txt`).

## Validation
- ALT re‑audit: 0 missing on products after fills.
- Robots: Staging preview returns custom policy; template is picked up.
- Schema: Will validate via Rich Results Test and source checks post‑deploy.

## Risks & Safeguards
- ALT updates: Low risk; product‑media API only; pages add‑only avoids overwrites.
- Renames: Higher blast radius; stage first, QA, then publish.
- Schema: Avoid duplicates; remove legacy JSON‑LD after new snippets are live.

## Rollback
- Products: ALT can be reverted per image in Admin if needed.
- Staging theme: Duplicate again to discard changes; Files uploads persist but are harmless.
- Robots/Schema: Remove the template/snippets and the render line to restore defaults.

## Next Steps (Recommended)
- Complete schema deployment on staging (via API or quick paste) and validate:
  - Home: Organization/WebSite
  - PDP: Product (Offer, GTIN/MPN if available)
  - Article: Article
- Ship ai.txt / llms.txt (Files + redirects) on staging, then live.
- Begin staged image‑rename batches:
  - Batch 1: Homepage + top products (rename + references) in staging; QA; publish.
- Editorial blog ALT:
  - Generate article fixpacks (per‑article suggested ALT) → review → apply add‑only.
