# Label Lens Webapp — MVP Requirements

**Status:** Draft for review
**Owner:** Piyush Bhandari
**Last updated:** 2026-08-17

## 1. Overview

Label Lens is a browsing and discovery tool for supplement products that makes ingredient and certification claims legible — specifically, the gap between what a label *implies* ("FDA registered facility," "GMP certified") and what's actually independently verified (NSF Certified for Sport, Informed Choice, USP Verified). The inspiration is [Cotina](https://cotinashop.com), a "material based shopping" site for clothing that lets health-conscious shoppers filter apparel by fabric composition and certification rather than brand or price. Label Lens applies the same discovery model to consumer products, starting with protein powder.

This is not e-commerce. There's no cart, no checkout, no accounts. It's a filterable directory: browse, filter down to what matters to you, read a transparent product page, and (eventually) get pointed to where you can buy it. For the MVP, that last step is intentionally a stub — see [§9](#9-known-data-gaps--follow-up-work).

## 2. Goals & Non-Goals

**Goals (MVP):**
- Browse and exhaustively filter the 396-product protein powder dataset by ingredient, certification, brand, category, and other label attributes.
- Present each product's trust signals honestly — real independent certification, clearly separated from self-asserted claims.
- Look and feel like a finished consumer product, not a data dump. Cotina is the visual/UX bar.
- Run session-only, no login.
- Keep the dataset itself refreshable without a rebuild of the app.

**Non-goals (MVP):**
- No e-commerce, cart, or checkout.
- No real outbound retailer links (Amazon, Whole Foods, iHerb) — see [§9](#9-known-data-gaps--follow-up-work).
- No price display — not in the current dataset.
- No user accounts, saved profiles across devices, or cross-session persistence.
- No categories beyond protein powder (whey/plant/pea/casein/collagen) — broader "consumer products" is future scope ([§10](#10-future-scope-post-mvp)).

## 3. Target User

Health-conscious supplement buyers — particularly athletes and anyone subject to drug testing — who've been burned by labels that *read* as certified but aren't, and who want to filter out ingredients (artificial sweeteners, proprietary blends, specific allergens) without reading a label in a supplement aisle or squinting at a product photo on Amazon.

## 4. Data Source & Content

**Current dataset:** [`data/dataset_full.json`](../data/dataset_full.json) — 396 products, 266 on-market, 211 brands, across:

| Category | Products | On market |
|---|---|---|
| Whey | 150 | 99 |
| Plant | 105 | 82 |
| Pea | 61 | 28 |
| Casein | 21 | 18 |
| Collagen | 59 | 39 |

Sourced from the NIH DSLD v9 API via the existing `label-lens` Python pipeline (`labellens/dsld.py`, `labellens/taxonomy.py`, `build_dataset_full.py`), deduped to distinct brand+formula combinations with whey capped at 150 so it doesn't dominate the much smaller casein/collagen categories.

**Per-product fields available today:** brand, product name, UPC, on/off-market status, entry date, manufacturer, serving size, full macro panel (calories, protein, fat, carbs, sugar, fiber, sodium, calcium, potassium), full ingredient list with taxonomy categories (protein source, artificial sweetener, filler/bulking agent, allergen source, etc.), allergen declarations, proprietary blend flags, and the Trust object (see [§6](#6-trust--certification-presentation)).

**Refresh cadence:** The pipeline is self-throttled and checkpointed (`build_dataset_full.py`), so it's safe to re-run periodically rather than once. MVP requirement: a scheduled job re-runs the pull (proposed: monthly, adjustable) and the app picks up the new `dataset_full.json` on next deploy or read — no manual data entry. Exact scheduling mechanism (cron, GitHub Action, etc.) is an implementation decision, not a product requirement.

## 5. Core Features (MVP)

### 5.1 Browse & category navigation
Top-level navigation by protein category: Whey, Plant, Pea, Casein, Collagen, plus an "All" view. Mirrors Cotina's Tops/Bottoms/Dresses pattern.

### 5.2 Exhaustive filtering
Filtering is a primary feature, not an afterthought — it should cover everything the dataset can support:
- **Ingredient — has / does not have**, multi-select, searchable (e.g. "no sucralose," "contains stevia")
- **Certification** — multi-select across the six real certifiers (NSF Certified for Sport, NSF Contents Certified, Informed Sport, Informed Choice, USP Verified, BSCG), plus an explicit "no independent certification" option
- **Category** (protein type)
- **Brand** — multi-select
- **Allergens** — exclude by allergen (milk, soy, egg, wheat, etc.)
- **Flags** — artificial sweetener present, proprietary blend present, on-market only
- **Macros** — protein % by weight range, calories range (stretch — see [§8](#8-technical-architecture-proposed) for whether this ships in MVP or v1.1)

Filters combine with AND logic across categories (e.g. "Whey" AND "no artificial sweetener" AND "NSF Certified for Sport") and OR logic within a single filter's selections (e.g. "NSF Certified for Sport" OR "USP Verified").

### 5.3 Search
Full-text search by brand or product name, usable alongside filters (matches Cotina's separate search entry point).

### 5.4 Product grid
Card view: product photo (see [§5.7](#57-product-photos)), brand, product name, category, protein % by weight, and a trust badge (certified / claims-only-no-cert / neither) so the headline signal is visible without opening the product.

### 5.5 Product detail page
- Photo, brand, name, category, serving size
- Full macro panel
- Full ingredient list, each ingredient tagged with its taxonomy category
- Allergen declarations
- **Trust section** — see [§6](#6-trust--certification-presentation), this is the differentiating feature and should be visually prominent, not buried
- Link to the DSLD source label (always available — this is real data we already have)
- "Get this product" button — MVP behavior is a disabled/stub state (see [§9](#9-known-data-gaps--follow-up-work))
- Favorite toggle

### 5.6 Favorites
Heart/favorite icon on cards and detail pages, matching Cotina. Session-scoped via browser storage (localStorage) — no account, no cross-device sync. "The current session is the account."

### 5.7 Product photos
Cotina sources real product photography; our DSLD dataset has none. MVP requirement: source a representative photo per product from the brand's own website where reasonably available, with a clean placeholder (e.g. a generic tub silhouette per category) when it isn't. This is a content-sourcing task, not just a UI one — see [§9](#9-known-data-gaps--follow-up-work) for scope and risk.

## 6. Trust & Certification Presentation

This is the feature Cotina doesn't have, and the reason this product exists. The dataset already distinguishes two things that look identical on a label:

- **Real independent certification** (`trust.certifications`) — a third party actually tested the product. Each certifier has a defined scope (e.g. NSF Certified for Sport and BSCG test every batch for banned substances; USP Verified confirms label accuracy but says nothing about banned substances; Informed Choice samples from retail rather than every batch). The UI should show *which* certifier and *what it actually covers*, not just a generic "certified" checkmark — collapsing that distinction is exactly the confusion this app exists to fix.
- **Self-asserted claims** (`trust.gmp_claimed`, `trust.fda_registration_claimed`, etc.) — printed on the label, true, and not verification of the product itself (FDA registration is a fact about a facility's address, not the product).

Every product detail page must clearly show one of three states:
1. **Independently certified** — badge naming the certifier(s) and, on hover/expand, what each one actually covers.
2. **Claims without verification** (`implies_approval_without_verification`) — an explicit warning-style callout: "This label references FDA registration / GMP compliance but carries no independent certification." This is the pattern worth flagging and should not be visually softer than the "certified" state.
3. **Neither claimed nor certified** — neutral, no claim either way.

## 7. UX / Design Direction

Cotina is the direct visual reference: teal/warm gradient header, category nav bar, a filter row of dropdown chips above a clean product grid, expandable sections on the detail page, minimal chrome. The bar for MVP is "looks like a real, shipped consumer product" — not a spreadsheet with a UI bolted on, even though the backing data is a periodically-refreshed static dataset rather than a live inventory feed.

## 8. Technical Architecture (proposed)

- **Data layer:** existing `label-lens` Python pipeline as source of truth. `dataset_full.json` is the canonical export the app reads from.
- **Frontend/backend split:** open implementation decision — a static-site generator reading the JSON at build time (simplest, matches "no accounts, no live writes") vs. a small API serving the same JSON. Recommend starting static; revisit if filtering performance or freshness needs push toward a live API.
- **Filtering:** client-side is very likely sufficient at 396 products; revisit if the dataset grows an order of magnitude.
- **Favorites:** browser localStorage, no backend persistence.
- **Refresh pipeline:** scheduled re-run of `build_dataset_full.py`, output redeployed. Mechanism (cron, GitHub Action, etc.) is an implementation detail, not specified here.

## 9. Known Data Gaps & Follow-Up Work

Called out explicitly because they change what "Get this product" and product photos can honestly do in MVP:

- **No real retailer links.** The dataset has no Amazon/Whole Foods/iHerb URLs, and DSLD doesn't provide them. MVP ships the "Get this product" button as a stub — either disabled with a "link not available yet" tooltip, or a lightweight notification on click. Wiring this up for real is a separate, later data-matching project (matching 396 DSLD records to live retailer listings is nontrivial and out of scope here).
- **No product photography.** Sourcing photos from brand websites per product is a real content task — likely a mix of scripted lookup and manual spot-checking, with a placeholder fallback required regardless of coverage achieved. Treat as a discrete work item, not a UI afterthought.
- **No price data.** Out of scope for MVP entirely; not currently sourced from DSLD.

## 10. Future Scope (Post-MVP)

- Expand beyond protein powder into other consumer product categories (the original "for consumer products broadly" vision).
- Real outbound retailer links once the data-matching problem is solved.
- Price data, if a source is found.
- Accounts with cross-device favorites.
- Mobile app.

## 11. Success Criteria / Definition of Done for MVP

- All 396 products across the 5 categories are browsable and every filter in [§5.2](#52-exhaustive-filtering) works correctly against the real dataset.
- Every product detail page correctly renders the three-state trust presentation from [§6](#6-trust--certification-presentation) with no false "certified" states (verified against the automated test suite's certification-detection tests).
- Search and favorites work as specified.
- The data refresh job runs on schedule and the app reflects a new pull without a code change.
- A first-time visitor with no context can look at the site and describe what it's for and what makes it different from a generic supplement listing, without being told.

## Appendix: How this doc was built

Drafted through a structured requirements session referencing [Cotina](https://cotinashop.com) as a live UX example, walked through directly (category nav → filter bar → product grid → product detail → outbound "Take Me to Product Page" link) before mapping each piece onto the Label Lens data model.
