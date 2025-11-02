# Deploy Schema + Robots (Shopify)

Use these instructions for the staging theme first (ID you provided). Once validated, repeat on the live theme.

## Files Provided Here

 - `shopify/snippets/geo-schema.liquid` — sitewide Organization + WebSite + Breadcrumb + delegates Product/Article.
- `shopify/snippets/schema-product.liquid` — PDP JSON‑LD with price/availability, SKU/GTIN (auto from barcode).
- `shopify/snippets/schema-article.liquid` — Blog post JSON‑LD.
- `shopify/robots.txt.liquid` — Custom robots including LLM allowances.
- `docs/ai.txt` and `docs/llms.txt` — Simple “Allow all” policies for AI crawlers.

## Install Steps (Staging Theme)

1) In Shopify Admin → Online Store → Themes → Edit code (staging theme):
   - Create files and paste the contents:
     - `snippets/seo-schema.liquid`
     - `snippets/schema-product.liquid`
     - `snippets/schema-article.liquid`
   - Open `layout/theme.liquid`, in `<head>` add:
     - `{% render 'geo-schema' %}` (preferred)
     - Backwards‑compatible: `{% render 'seo-schema' %}` still works; it delegates to `geo-schema`.

2) Product + Article pages
   - No extra wiring needed: `seo-schema` will include product/article schema when on those templates.

3) Robots
   - Create `robots.txt.liquid` at the theme root and paste from `shopify/robots.txt.liquid`.
   - Save. Verify at: `https://yourdomain.com/robots.txt?preview_theme_id=THEME_ID`.

4) ai.txt / llms.txt
   - Settings → Files → Upload `docs/ai.txt` as `ai.txt` and `docs/llms.txt` as `llms.txt`.
   - Online Store → Navigation → URL redirects → Add 2 redirects:
     - `/ai.txt` → paste the Files URL of `ai.txt`
     - `/llms.txt` → paste the Files URL of `llms.txt`
   - Test: `https://yourdomain.com/ai.txt?preview_theme_id=THEME_ID`

## Cleanup Previous Schema (avoid duplicates)

1) Search code for `type="application/ld+json"`.
2) For any theme files that output older schema:
   - Either comment them out, or
   - Move their content into `snippets/legacy-schema-archive-YYYY-MM-DD.liquid` for reference, then remove the inline script tags.

## Validation

- Google Rich Results Test: validate a PDP and a blog post.
- View-source: confirm only one Organization/WebSite/Product/Article JSON‑LD block each.
- robots: confirm AI crawlers listed and sitemap present.
