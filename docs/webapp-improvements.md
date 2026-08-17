# Label Lens Webapp — Improvement Backlog

**Status:** Proposed
**Last updated:** 2026-08-17
**Context:** Post-MVP review of `webapp/`, prompted by (a) filter logic behaving
illogically and (b) the plan to expand beyond protein powders.

**How this was tested:** a data-quality audit across all 396 products, plus a
live session driving the running app — render/DOM measurement, navigation and
back-button state, filter journeys, empty states, and an accessibility probe.
Items marked **[verified]** were reproduced against the real dataset or the
running site. The rest are design judgments.

---

## §1 · P0 — Correctness and safety

These undermine the product's core promise. A site whose thesis is *"labels
mislead you"* cannot itself display things that are wrong.

### 1.1 The allergen filter silently fails, and it's the dangerous direction **[verified]**

**60 products containing whey, casein, lactose or milk survive an "exclude
milk" filter**, because DSLD carries no allergen declaration for them and the
app treats *absent data* as *absent allergen*.

Real examples a milk-allergic user is shown after excluding milk:

| Product | Declared allergens | Actual ingredients |
|---|---|---|
| Body Attack 100% Whey Protein Apricot Yoghurt | *(none)* | Whey Protein Concentrate, **Milk** |
| Body Attack 100% Whey Protein Apfelstrudel | *(none)* | **Lactose**, Whey Protein concentrate |
| BioChem Sports 100% Whey Protein Chocolate | *(none)* | Whey Protein Isolate |
| NOW Sports Certified Organic Whey Protein | *(none)* | organic Whey Protein concentrate |

44% of the catalogue (176/396) declares no allergens at all. **[verified]**

**Fix — three parts, all needed:**
1. Derive allergens from ingredients using the taxonomy's existing
   `ALLERGEN_SOURCE` tag, and union with declared allergens.
2. Model three distinct states — `declared present` / `declared free` /
   **`not declared`** — and never let the third read as the second.
3. Re-frame the filter as *"exclude products that declare or contain X"* and
   warn on results with no declaration. Never assert a product is allergen-free.

This is the single highest-priority item in this document.

### 1.2 26 products display impossible protein percentages, up to 2500% **[verified]**

Live on cards right now: *"2500% protein"*, *"262% protein"*, *"142% protein"*.

Root cause is in the Python model, not the UI: `Macros.protein_pct_by_weight()`
divides grams of protein by the serving *quantity* while ignoring the serving
*unit*. When a label declares "1 Scoop" or "1 Ounce" instead of grams, 28g ÷ 1
scoop renders as 2800%.

Serving units in the dataset: 380 `Gram(s)`, plus 16 products using
`Scoop(s)`, `Packet(s)`, `Ounce(s)`, `Tbsp`, `Tablet(s)`, `Capsule(s)`, `mg`. **[verified]**

**Fix:** compute the ratio only for mass units; convert where a conversion
exists (1 oz = 28.35 g); return `None` for scoops/packets/capsules and show
"not comparable" rather than a fabricated number. Add a guard test asserting no
product ever exceeds 100%.

### 1.3 43% of product pages show "Ingredients (0)" above the real ingredients **[verified]**

169 of 396 products have an empty `ingredients` list while their actual
composition sits under `other_ingredients`. The page renders a bare
**"Ingredients (0)"** header, then lists the real contents — including the main
protein source — under "Other ingredients" below it.

**Fix:** merge into a single list when `ingredients` is empty, or suppress the
empty heading. Keep the DSLD distinction in the data; stop surfacing it as a
contradiction.

### 1.4 No data-quality gate between pipeline and site

The three issues above all reached production because nothing checks the data
on the way out. Add an assertion pass to `prepare_data.py` — protein % ≤ 100,
serving units recognised, ingredient list non-empty, category present — that
fails the build loudly rather than shipping a 2500% figure.

---

## §2 · P0 — Filter logic (the reported problem)

### 2.1 Within-facet AND/OR is inconsistent, and the documentation is wrong **[verified]**

The rule stated in `docs/webapp-prd.md` §5.2 and in the comment on
`matchesFilters()` — *"AND across groups, OR within a group"* — **was never what
the code did**:

| Facet | A product has… | Current | Should be |
|---|---|---|---|
| Certification | many certs | **OR** (`.some`) | **AND** |
| Has ingredient | many ingredients | AND (`.every`) | AND |
| Does not have ingredient | many ingredients | AND (excl. all) | AND |
| Exclude allergen | many allergens | AND (excl. all) | AND |
| Brand | **exactly one** | OR | OR — AND is degenerate |
| Category / type | **exactly one** | single-select | OR when multi-select |

The principle worth adopting, because it explains every row:

> **Within-facet semantics follow the field's cardinality.** A product holds a
> *set* of certifications and ingredients, so both "has all of these" (AND) and
> "has any of these" (OR) are meaningful. A product has exactly *one* brand and
> one category, so AND across two selections is always empty — those can only
> be OR.

**Action:** switch certification to AND, fix the comment in `apply.ts`, and fix
PRD §5.2 so the documented rule matches reality.

### 2.2 AND on certifications is near-empty without facet counts — ship them together **[verified]**

Certification coverage in the current data:

- **371 of 396 products carry no certification at all**
- 15 carry one, 10 carry two
- Informed Choice 18 · Informed Sport 14 · NSF Certified for Sport 2 · BSCG 1
- **Only one certifier pair co-occurs anywhere:** Informed Choice + Informed
  Sport (10 products). *Every other two-certifier AND returns zero.*

AND is the right semantics but a cliff edge in practice. Ship it alongside:

- **Facet counts** — `NSF Certified for Sport (2)`, recomputed against the other
  active filters.
- **Zero-result options disabled**, not clickable into an empty page.
- **An `Any` / `All` toggle** per multi-value facet, defaulting to `All`.

### 2.3 Ingredient autocomplete silently hides ~70% of ingredients **[verified]**

`TagSearchInput` caps its `<datalist>` at `options.slice(0, 400)` while the
dataset holds **1,336 distinct ingredient names**. Alphabetically the cut lands
at "Ferrous Fumarate":

| Ingredient | Index | Suggested? |
|---|---|---|
| Whey Protein | 2 | yes |
| Pea Protein | 3 | yes |
| Stevia extract | 925 | **no** |
| Sucralose | 1182 | **no** |
| Xanthan Gum | 1322 | **no** |

The field's placeholder is *"e.g. sucralose"* — it suggests the one ingredient
it then fails to autocomplete. **Fix:** filter by typed text first, cap after.

### 2.4 Free-text filter values accepted with no validation

Typing `asdf` adds a chip matching nothing, with no signal distinguishing "no
products have this" from "that isn't an ingredient."

### 2.5 Ingredient matching is naive substring

`n.includes(needle)` powers *allergen avoidance*, where a false negative is the
costly direction. Move to word-boundary matching, and prefer the taxonomy
category (`artificial_sweetener`) over raw name where one exists.

### 2.6 `isEmpty()` compares filters via `JSON.stringify` **[verified]**

`filters/types.ts:30` — key-order dependent. Works only because
`filtersFromParams` happens to build keys in `EMPTY_FILTERS` order. Any added
field or reordering spread breaks "Clear all" silently. Compare field-wise.

### 2.7 Default ordering is arbitrary **[verified]**

The unfiltered grid renders in dataset order, so certified products sit
scattered among uncertified ones. For a site built on surfacing verification,
certified-first is the obvious default. See also §8.1 (sorting).

---

## §3 · P1 — Room for more product types

Today "category" means *whey / plant / pea / casein / collagen* — a
protein-powder sub-type. A second vertical has nowhere to go.

### 3.1 Split `category` into `vertical` + `subtype`

```
vertical: 'protein_powder' | 'creatine' | 'multivitamin' | …
subtype:  'whey' | 'plant' | …        (scoped per vertical)
```

### 3.2 Replace hardcoded protein assumptions with a per-vertical registry

| Location | Coupling |
|---|---|
| `data/types.ts` | `ProteinCategory` union, `CATEGORY_LABELS` |
| `components/Header.tsx` | `CATEGORIES` nav array |
| `components/ProductCard.tsx` | protein-%-by-weight as *the* headline metric |
| `components/FilterBar.tsx` | "Min. protein by weight" |
| `filters/types.ts` | `minProteinPct` |
| `build_dataset_full.py` | `KEYWORDS`, `WHEY_CAP`, whey-specific cap logic |
| `webapp/scripts/prepare_data.py` | imports the protein-specific `build_selection` |

One registry per vertical declaring: display name, subtypes, applicable filters,
and headline card metric. Protein % is meaningless on a multivitamin; elemental
dose is meaningless on whey. Components read the registry instead of constants.

### 3.3 Per-vertical taxonomy coverage pass

`taxonomy.py` extends fine structurally but was tuned on protein powders. Each
new vertical needs a `coverage()` / `unmapped()` pass before launch or its
ingredients land in `OTHER` and quietly break filtering. Make it a documented
step in an add-a-vertical checklist.

---

## §4 · P1 — Performance and delivery

### 4.1 Reconsider bundling the dataset into the JS

I changed `useDataset` to `import` the JSON at build time so the app could ship
as one self-contained file. Right for a single-file share, wrong at scale — the
entire catalogue currently lands in the main bundle. With several verticals,
fetch per-vertical JSON, chunked and cached, so someone browsing creatine never
downloads the protein catalogue.

### 4.2 Virtualise the grid **[verified]**

All 396 matching products render at once — 7,184 DOM nodes on first paint.
Fine now, sluggish in the low thousands. Add list virtualisation.

### 4.3 Index the filters

`matchesFilters` is a full O(n × facets) scan per keystroke. Precompute inverted
indexes (ingredient → ids, certifier → ids) and intersect sets instead.

---

## §5 · P1 — What would take it to the next level

The MVP is a competent catalogue browser. These are what separate it from one,
drawn from how comparable products solve the same problem.

### 5.1 A transparent Label Confidence score — the signature feature

Every serious product in this space leads with one opinionated number: EWG Skin
Deep's 1–10 hazard score, Yuka's 0–100, Labdoor's purity rank. Users cannot hold
twelve attributes in their head; they want a verdict.

Label Lens has the raw material already: certification tier and scope, presence
of proprietary blends, ingredient count, allergen declaration completeness,
protein density, artificial-sweetener presence.

**The critical constraint:** the score must be fully auditable — show the
components, the weights, and the arithmetic on the product page, and let users
re-weight what matters to them. A black-box score would commit exactly the sin
this product exists to expose. That transparency is itself the differentiator.

### 5.2 "Better alternatives" on every weak product

Yuka's stickiest feature: when a product scores poorly, immediately show better
ones. On a *"claims, no verification"* page, surface certified products in the
same subtype with comparable macros. This converts the app's insight into an
action, which is the difference between an interesting fact and a decision.

### 5.3 Normalised comparison — the analytical spine

Serving sizes range from a 6.4 g collagen scoop to a 42 g casein scoop, so
per-serving figures aren't comparable. Add a **per-100 g** (and per-30 g) view
across macros, and make it the default basis for ranking. If price data ever
lands, **cost per gram of protein** is the number this category actually buys on.

### 5.4 A compare tray

Select 2–4 products, see a side-by-side diff of macros, ingredients, and trust —
with differences highlighted. Standard in every serious comparison tool
(PCPartPicker, RTINGS) and absent here.

### 5.5 Barcode scan — the mobile killer feature, already unlocked by the data

**351 of 396 products carry a UPC** **[verified]**. Yuka's entire product is
"scan it in the aisle." Standing in a shop holding a tub, scanning it to get the
certification breakdown is a far stronger use case than browsing at a desk — and
the data to support it already exists. Pairs naturally with a PWA/offline build.

### 5.6 Ingredient and certifier detail pages

EWG gives every ingredient its own page. Here: *"Sucralose — what it is, which
53 products contain it"*, and *"Informed Choice — what it actually tests, which
18 products carry it, how it differs from Informed Sport."* Genuinely useful,
and a large organic-search surface (§6).

### 5.7 Curated collections as real pages

"NSF Certified for Sport whey", "No artificial sweeteners", "Highest protein
density", "Fewer than five ingredients" — saved filter states presented as
browsable, linkable landing pages. This is how Cotina's own category structure
works, and it doubles as the SEO strategy.

### 5.8 A methodology page

Trust products live or die on explaining themselves: where the data comes from
(DSLD), how certifications are detected (label text matching, not a certifier
database join), what "off market" means, and known limitations — including the
allergen gap in §1.1. Publishing limitations *builds* credibility here.

### 5.9 Saved requirement profiles

Let someone persist "no dairy, certified only, no artificial sweeteners" once
and have it applied by default. For a person with an allergy or a tested
athlete, that's the difference between a tool and a toy. Favorites already
prove the storage pattern.

### 5.10 A data-correction feedback loop

Given §1.2's 2500% figures and §1.1's missing allergens, upstream data *will* be
wrong. Open Food Facts is community-corrected; Cotina ships a FEEDBACK nav item.
A per-product "report an issue" affordance turns users into a QA channel.

### 5.11 Editorial content

The thesis — FDA registration is a fact about an address, not an approval —
needs explaining somewhere other than a badge tooltip. Short guides on what each
certification covers and what a proprietary blend hides are both the product's
voice and its most durable acquisition channel.

---

## §6 · P1 — Discoverability

### 6.1 The site is currently invisible to search engines

`HashRouter` plus client-side rendering means no crawlable URLs and no
server-rendered content. For a site whose natural demand is people googling *"is
X protein powder NSF certified"*, that forecloses the main growth channel. 396
product pages, plus ingredient and collection pages, are the asset.

**Needs:** real path-based routes (not `#/`), static pre-rendering or SSR,
per-page `<title>` and meta description, Open Graph tags, `schema.org/Product`
structured data, `sitemap.xml`, canonical URLs.

Note the tension with §4.1 and the single-file artifact build — pick one:
shareable single file *or* indexable multi-page site. For a public product it
should be the latter, with the single-file build kept as a side target.

### 6.2 The document title never changes **[verified]**

Every route is titled "Label Lens" — including product pages. Bad for tabs,
history, bookmarks, screen readers, and search results alike.

---

## §7 · P1 — Accessibility

Probed on the running site **[verified]**:

| Check | Result |
|---|---|
| Filter checkbox labels | ✅ correctly associated |
| `:focus-visible` styling | ❌ **no rule anywhere** — keyboard focus is invisible |
| `<main>` landmark | ❌ absent |
| Skip-to-content link | ❌ absent |
| Per-route `<h1>` | ⚠️ one, but static across routes |

Keyboard-only operation of the facet list is effectively untested. Given the
audience includes people managing medical dietary restrictions, accessibility
is core, not polish.

---

## §8 · P2 — UX gaps

1. **No sorting.** Certified-first, protein density, name. See §2.7.
2. **Off-market products are 33% of the catalogue** (130/396) **[verified]**,
   shown by default behind a small corner badge. Default to on-market or sort last.
3. **No scroll-to-top on navigation** **[verified]** — clicking a product from a
   scrolled grid opens the product page already scrolled down (measured: 1453px).
   *(Filter state and scroll position do correctly survive the back button.)*
4. **No active-filter chips or per-filter clear** — only "Clear all".
5. **Dead-end empty state** **[verified]** — *"No products match these filters."*
   with no recovery path. Name the most restrictive facet and offer to relax it.
6. **Search requires Enter and covers only brand/product name** — no ingredient
   search, no live results, no typo tolerance ("sucrolose" finds nothing).
7. **Brand facet has 211 entries** **[verified]** in a flat list.
8. **Multi-cert badge collapses to "2 certifications"**, dropping exactly the
   distinction the product exists to make.
9. **Mobile puts the entire filter column above the grid** **[verified]** — users
   scroll past every facet to reach products. Needs a drawer or bottom sheet.
10. **Product photos are placeholder initials** (PRD §5.7 / §9, still open).
11. **No loading, error, or empty-favorites states** worth the name.

---

## §9 · P2 — Data fidelity

1. **`match_confidence` is never surfaced.** `schema.py` says below ~0.9 a human
   should review before it reads as verified; the UI treats every certification
   as equally solid. Latent today (all detections are 1.0) but a real gap once
   certifier-list joins land.
2. **`dataset.generated` is never shown.** The PRD promises a refresh pipeline;
   users should see data freshness.
3. **`nutrient_panel` isn't filterable** — no "has iron", despite now being parsed.
4. **Off-market means "label withdrawn from DSLD"**, not necessarily
   discontinued — currently unexplained anywhere in the UI.

---

## §10 · P2 — Engineering

1. **The webapp has zero tests** while the pipeline has 33. `matchesFilters`,
   `matchesSearch`, and the params↔state round-trip are pure functions — the
   natural starting point, ideally *before* changing AND/OR semantics so the
   change is pinned by tests.
2. **No CI.** `pytest` + `tsc --noEmit` + `oxlint` on push is a few lines.
3. **No error boundary** — one bad record blanks the page.
4. **`useFavorites` is a hand-rolled store** with module-level mutable state and
   a listener array. Fine at this size; revisit if state grows.

---

## Suggested sequence

**1 — Stop being wrong (§1).** Allergen derivation and the three-state model,
the protein-% unit bug, the "Ingredients (0)" merge, and the data-quality gate.
These are credibility-critical and mostly small.

**2 — Make filtering sane (§2).** Certification AND + facet counts + zero-state
disabling, the autocomplete cap, `isEmpty`, default sort. Land filter unit tests
(§10.1) first so the semantics change is pinned.

**3 — Open the architecture (§3).** Vertical/subtype split and the registry,
*before* a second product type turns a refactor into a migration.

**4 — Earn the audience (§6, §5.7, §5.8).** Real routes, pre-rendering, per-page
metadata, curated collections, methodology page. Nothing else matters if nobody
can find it.

**5 — Differentiate (§5.1–5.5).** Confidence score, alternatives, normalised
comparison, compare tray, barcode scan.

**6 — Polish continuously (§7, §8).** Accessibility and the UX gaps alongside
each of the above rather than as a final pass.
