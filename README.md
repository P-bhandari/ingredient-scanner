# label lens

**A searchable, filterable database of protein powders — ingredients, macros, and what their regulatory claims actually mean.**

Working name. Alternatives at the bottom.

---

## ⚠️ Read this first: one premise in the original brief is wrong, and it matters

The brief asked for a filter for **"is this FDA approved?"**

**The FDA does not approve dietary supplements.** Not protein powders, not any of them.

Under the Dietary Supplement Health and Education Act of 1994 (DSHEA), the FDA is *not authorised* to approve dietary supplements for safety or efficacy before they go on sale. In many cases a company can lawfully put a supplement on the market **without notifying the FDA at all**. Supplements are regulated as a category of food, and responsibility for safety and labelling sits with the manufacturer, not the regulator.
([FDA — Questions and Answers on Dietary Supplements](https://www.fda.gov/food/information-consumers-using-dietary-supplements/questions-and-answers-dietary-supplements) · [FDA 101: Dietary Supplements](https://www.fda.gov/consumers/consumer-updates/fda-101-dietary-supplements))

Every supplement label in the US carries this legally mandated disclaimer, which says so explicitly:

> *"These statements have not been evaluated by the Food and Drug Administration. This product is not intended to diagnose, treat, cure or prevent any disease."*

**Why this is not pedantry.** A health app shipping an "FDA approved ✓" filter would be actively misleading users about safety, on the exact axis they came to the app to check. It's the sort of error that gets a health product written about for the wrong reasons. It is also, usefully, *the strongest reason for this app to exist* — most people believe supplements are approved, and they are not.

### What actually exists, and what we filter on instead

| Signal | What it means | Reality |
|---|---|---|
| **FDA facility registration** | The manufacturer registered its facility. A mailing address, essentially. | Not a quality signal. Manufacturers print it to *imply* approval. |
| **cGMP (21 CFR 111)** | Manufacturing process rules; FDA inspects facilities periodically. | Process compliance, not product testing. |
| **NSF Certified for Sport** | **Every batch** tested. Screens 280+ banned substances plus undeclared ingredients. Recognised by USADA, MLB, NHL, CFL. | Strongest widely available signal. |
| **Informed Sport** | Batch-by-batch banned-substance testing by LGC, a WADA-accredited lab. | Comparable to NSF for Sport. |
| **USP Verified** | Verifies label accuracy, identity, potency, purity; GMP facility. **Does not** test banned substances. | Strong on "the label is true", silent on contamination. |
| **EU** | Supplements fall under Directive 2002/46/EC — notification-based, no pre-market approval either. EFSA authorises *health claims*, not products. | "EU approved" is likewise not a thing. |

**So the filter axis is not approval. It is: who independently tested this, what did they test for, and was it every batch or one sample?** That is a genuinely useful distinction and almost no consumer-facing tool makes it.

---

## The data source: don't scrape, use DSLD

The brief suggested scraping websites for products, ingredients and macros. There's a much better option.

**[NIH Dietary Supplement Label Database (DSLD)](https://dsld.od.nih.gov/)** — from the NIH Office of Dietary Supplements:

- **200,000+** supplement labels, transcribed from the actual physical packaging
- Full ingredient rows with quantities, units and %DV
- **Pre-assigned ingredient categories** (`protein`, `fat`, `sugar`, `mineral`, `botanical`, `non-nutrient/non-botanical`, …)
- **UNII codes** — FDA's unique ingredient identifiers, so ingredients join reliably across products
- Label statements: allergens, claims, seals, the DSHEA disclaimer, storage, directions
- Manufacturer name and address
- `offMarket` flag and entry dates
- Public REST API: `https://api.ods.od.nih.gov/dsld/v9/`
- **1,000 requests/hour** without a key, 10,000 with a free data.gov key
- **Licence: CC0 1.0 — public domain.** No permission needed, attribution requested.
  ([API Guide](https://dsld.od.nih.gov/api-guide))

Verified live while building this: `browse-products?q=whey protein` returns **1,159** products.

**This beats scraping on every axis that matters**: it's legal, it's stable, it's label-accurate rather than marketing copy, it's already normalised, and the ingredient categorisation the brief asked us to build is *partly done already*.

### The one thing DSLD does not have

Certifications. NSF, Informed Sport and USP each publish their own certified-product lists, so those are separate joins — matched on brand plus product name, and confidence-scored, because the naming never matches cleanly. This is the honest hard part of the build and where the real work sits.

---

## Data model

```
Product ─┬─ identity     dsld_id, brand, name, upc, off_market
         ├─ serving      size, unit, servings_per_container
         ├─ macros       calories, protein_g, fat_g, carbs_g, sugar_g, sodium_mg …
         ├─ ingredients  ─── Ingredient[]  (name, unii, category, qty, unit, %DV)
         ├─ flags        derived: has_artificial_sweetener, has_added_sugar,
         │               proprietary_blend, allergens[], vegan_claimed …
         └─ trust        certifications[], gmp_claimed, fda_reg_claimed,
                         dshea_disclaimer_present
```

The `trust` block is deliberately named that rather than `regulatory`, because it holds two different kinds of thing: **verified third-party certifications** and **claims the manufacturer printed about itself**. Conflating those is the error this whole project exists to correct.

---

## Ingredient → category taxonomy

DSLD gives a coarse category per ingredient. We layer a second, decision-useful taxonomy on top — the things a person actually filters on:

| Category | Examples |
|---|---|
| `protein_source` | whey isolate, whey concentrate, casein, pea, soy, rice, collagen |
| `artificial_sweetener` | sucralose, aspartame, acesulfame potassium, saccharin |
| `natural_sweetener` | stevia, monk fruit, erythritol, xylitol |
| `added_sugar` | sucrose, dextrose, maltodextrin, corn syrup solids |
| `thickener_emulsifier` | xanthan gum, soy lecithin, sunflower lecithin, carrageenan |
| `filler_bulking` | maltodextrin, dextrose, inulin |
| `digestive_enzyme` | protease, lactase, bromelain |
| `flavour_colour` | natural/artificial flavour, titanium dioxide, dyes |
| `allergen_source` | milk, soy, egg, tree nut, wheat |
| `stimulant` | caffeine, green tea extract |

Mapping is keyed on **UNII where available**, falling back to normalised name matching. UNII first matters: "sucralose", "Sucralose", and "Splenda®" are one ingredient, and only the identifier knows that.

---

## Status

**Not yet built.** This document is the design, and the data source and regulatory model are verified. Next up:

1. `dsld.py` — API client with rate limiting and caching
2. `schema.py` — the model above, in Pydantic
3. `taxonomy.py` — UNII-keyed ingredient mapping
4. `ingest.py` — pull protein powders, normalise, write to SQLite
5. Certification joins — NSF / Informed Sport / USP, fuzzy-matched and confidence-scored
6. Query layer, then UI

---

## Honest notes

**Verified:** that FDA does not approve supplements pre-market (FDA's own consumer pages); DSLD's size, licence, endpoints and rate limits (NIH API guide, plus live calls); that NSF for Sport and Informed Sport test every batch while USP Verified does not cover banned substances (certifier documentation).

**Not verified:** the EU position is from secondary sources and my own knowledge, not from EUR-Lex directly. **Read Directive 2002/46/EC before shipping any EU-facing claim.**

**Inference:** that certification joins will be the hardest part; that UNII-first matching is the right call. Both are engineering judgments, not findings.

**Not medical advice.** This surfaces label data and independent testing status. It does not assess whether a product is safe or suitable for anyone, and shouldn't imply that it does.

---

## Naming

| Name | Note |
|---|---|
| **`label lens`** | What it does: read the label properly. |
| `unspiked` | Refers to amino spiking, a real fraud in this category. Insider-legible. |
| `whatsinit` | Plain, memorable, broad enough to extend past protein. |
| `certcheck` | Leads with the differentiator, narrower. |
