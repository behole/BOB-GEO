# Schema.org Templates

Reference JSON-LD schema templates for Brush On Block.

These are **example templates** showing the structure and format of schema.org markup. The actual implementation uses dynamic Liquid snippets in `shopify/snippets/` that pull data from Shopify.

## Templates Included

- **schema-organization.json** - Organization/brand schema (example)
- **schema-website.json** - WebSite schema with search action (example)
- **schema-product-spf30-powder.json** - Product schema example (SPF 30)
- **schema-product-spf50-sheer-genius.json** - Product schema example (SPF 50)
- **schema-breadcrumb-product.json** - BreadcrumbList schema (example)
- **schema-faq.json** - FAQPage schema (example)
- **schema-howto-application.json** - HowTo schema (example)

## Implementation

These templates were used as references to build the dynamic Liquid snippets:
- `shopify/snippets/geo-schema.liquid` - Organization, WebSite, Breadcrumb
- `shopify/snippets/schema-product.liquid` - Product schema (dynamic)
- `shopify/snippets/schema-article.liquid` - Article/BlogPosting schema (dynamic)

## Usage

Use these as reference when:
- Creating new schema types
- Validating schema structure
- Understanding what data fields are needed
- Testing with schema validators

## Validation

Test schemas at:
- https://validator.schema.org/
- https://search.google.com/test/rich-results
