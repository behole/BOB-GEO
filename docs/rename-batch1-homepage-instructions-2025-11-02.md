# Homepage Image Filename Updates — Staging (Batch 1)

Use these steps to swap homepage images to GEO‑style filenames on the staging theme only (ID: 185693077873).

## Files to Upload (Shopify → Content → Files)
See: `audits/rename-batch1-homepage-2025-11-02.csv`
- KIDS_essentials_Mega.png → `brush-on-block-bob-kids-essentials-kit-hero.png`
- TOT_refill.png → `brush-on-block-touch-of-tan-refill.png`
- spf_30_0a3c767b-f416-4ef1-bd64-cdccaee5d57b.png → `brush-on-block-spf-30-mineral-powder-sunscreen.png`
- TOT_refill_DT.jpg → `brush-on-block-touch-of-tan-refill-desktop.jpg`
- TOT_refill_mobile.jpg → `brush-on-block-touch-of-tan-refill-mobile.jpg`
- peony.jpg → `brush-on-block-sun-shine-lip-oil-peony.jpg`

## Swap in Theme Editor (staging theme)
1. Shopify Admin → Online Store → Themes → On the staging theme (ID `185693077873`) click **Customize**.
2. On the homepage:
   - For hero/feature sections (e.g., Image banner, Slideshow, Rich text with image):
     - Select the section, locate the image picker(s).
     - Click **Change** → **Files**, search for the new filename (e.g., `brush-on-block-touch-of-tan-refill-desktop.jpg`).
     - Select and **Save**.
   - If the section has separate Desktop/Mobile images, update both.
3. Repeat for each item listed above. Save after each section or after all swaps.

## Verify (staging preview)
- Open: `https://brushonblock.com/?preview_theme_id=185693077873`
- Hard refresh (Cmd+Shift+R). Confirm:
  - No broken images.
  - Right‑click an updated image → Copy image address → it should include the new filename (e.g., `.../brush-on-block-spf-30-mineral-powder-sunscreen.png`).

## Rollback
- You can revert any individual image in the Theme Editor by selecting the previous file from Files.
- No live impact: changes are confined to the staging theme until you publish it.

---
Last updated: 2025-11-02
