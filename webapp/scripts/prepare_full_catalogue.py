"""
Builds the webapp's data files from the full DSLD supplement corpus.

Reads data/dataset_supplements_full.json -- roughly 350 MB, ~117,800 already
deduplicated products, produced separately by build_dataset_supplements.py --
and streams it (via ijson; the file is far too large to load whole) into:

    webapp/public/data/index.json         one compact row per product, used
                                           for browsing/filtering/searching/
                                           sorting the entire catalogue
                                           client-side
    webapp/public/data/shards/<n>.json    the full Product object for every
                                           product whose id % NUM_SHARDS == n,
                                           fetched lazily by the detail page
    webapp/public/data/meta.json          dataset.generated / citation /
                                           licence / total count, for the
                                           footer

Why sharded, not one bundle: this dataset is two orders of magnitude larger
than the 396-product protein-only catalogue, which was small enough to import
directly into the JS bundle. Nothing that size can ship in a browser tab, so
the index carries only what browsing needs, and full ingredient/trust/macro
detail is fetched per-product on demand.

Category is DSLD's own `product_type` classification (11 values), not a
hand-built taxonomy -- see PRODUCT_TYPE_TO_CATEGORY below. It is uneven
("Other Combinations" is over a third of the corpus), but it is NIH's own
classification rather than something inferred here, which matters on a site
whose whole premise is not overclaiming what the data supports.

    python webapp/scripts/prepare_full_catalogue.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

import ijson

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from labellens.schema import Product  # noqa: E402

SOURCE = ROOT / "data" / "dataset_supplements_full.json"
OUT_DIR = ROOT / "webapp" / "public" / "data"
SHARD_DIR = OUT_DIR / "shards"
NUM_SHARDS = 360

# DSLD's own product_type -> our category slug. Every value observed in the
# corpus is mapped explicitly; an unrecognised one is a hard failure (see
# check below) rather than a silent "other", because a category scheme that
# quietly swallows an unmapped bucket is exactly the kind of small lie this
# project exists to avoid making.
PRODUCT_TYPE_TO_CATEGORY: dict[str, str] = {
    "Other Combinations": "other_combinations",
    "Botanical": "botanical",
    "Non-Nutrient/Non-Botanical": "non_nutrient",
    "Botanical with Nutrients": "botanical_with_nutrients",
    "Vitamin": "vitamin",
    "Amino acid/Protein": "amino_acid_protein",
    "Fat/Fatty Acid": "fat_fatty_acid",
    "Mineral": "mineral",
    "Multi-Vitamin and Mineral (MVM)": "multivitamin_mineral",
    "Single Vitamin and Mineral": "single_vitamin_mineral",
    "Fiber and Other Nutrients": "fiber_other",
}
UNCATEGORIZED = "uncategorized"


def trust_state(product: Product) -> str:
    if product.trust.has_independent_verification:
        return "verified"
    if product.trust.implies_approval_without_verification:
        return "claim-only"
    return "neutral"


def enrich(product: Product, category: str) -> dict[str, Any]:
    """The full per-product record written to its shard -- same shape the
    protein-powder pipeline already produces, so ProductDetailPage and
    data/derived.ts need no changes to consume it."""
    data = product.model_dump(mode="json")
    data["category"] = category
    data["protein_pct_by_weight"] = product.protein_pct_by_weight
    data["protein_pct_basis"] = product.protein_pct_basis
    data["serving_grams"] = product.serving.grams
    data["allergens_all"] = product.allergens_all
    data["allergen_declaration_missing"] = product.allergen_declaration_missing
    return data


def index_row(product: Product, category: str, shard: int) -> dict[str, Any]:
    """The compact record used for browsing every one of ~117,800 products at
    once. Every field a filter, sort, search, or card needs to answer without
    fetching a shard -- and nothing else."""
    names = [i.name for i in product.ingredients + product.other_ingredients]
    return {
        "id": product.dsld_id,
        "brand": product.brand,
        "name": product.name,
        "category": category,
        "offMarket": product.off_market,
        "proteinPct": product.protein_pct_by_weight,
        "trustState": trust_state(product),
        "certifiers": sorted({c.certifier.value for c in product.trust.certifications}),
        "allergens": product.allergens_all,
        "allergenDeclarationMissing": product.allergen_declaration_missing,
        "ingredientNames": names,
        "hasArtificialSweetener": product.has_artificial_sweetener,
        "hasProprietaryBlend": product.has_proprietary_blend,
        "shard": shard,
    }


class ShardWriter:
    """Streams NUM_SHARDS JSON arrays in a single pass, one open file handle
    each -- avoids both re-reading the 350 MB source once per shard and
    buffering an entire shard's products in memory before writing."""

    def __init__(self, out_dir: Path, num_shards: int) -> None:
        self.num_shards = num_shards
        out_dir.mkdir(parents=True, exist_ok=True)
        self._handles: list[TextIO] = []
        self._first: list[bool] = []
        for n in range(num_shards):
            handle = (out_dir / f"{n}.json").open("w", encoding="utf-8")
            handle.write("[\n")
            self._handles.append(handle)
            self._first.append(True)

    def write(self, shard: int, record: dict[str, Any]) -> None:
        handle = self._handles[shard]
        if not self._first[shard]:
            handle.write(",\n")
        self._first[shard] = False
        json.dump(record, handle, ensure_ascii=False, separators=(",", ":"))

    def close(self) -> None:
        for handle in self._handles:
            handle.write("\n]\n")
            handle.close()


def check_quality(index: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """
    Same split as the protein-powder gate: errors are things that would be
    actively wrong to publish (block the build); warnings are honest gaps in
    the upstream data (report, don't block). The protein-density check from
    the smaller gate is dropped here -- most of this corpus isn't protein
    products, so "no derivable protein %" is the expected case, not a defect.
    """
    errors: list[str] = []
    warnings: list[str] = []
    seen_categories = {c for c in PRODUCT_TYPE_TO_CATEGORY.values()} | {UNCATEGORIZED}

    for row in index:
        pid = f"{row['id']} ({row.get('brand', '?')})"
        pct = row.get("proteinPct")
        if pct is not None and not (0 < pct <= 100):
            errors.append(f"{pid}: proteinPct={pct} outside 0-100")
        if row.get("category") not in seen_categories:
            errors.append(f"{pid}: unrecognised category {row.get('category')!r}")
        if not isinstance(row.get("allergens"), list):
            errors.append(f"{pid}: allergens missing or not a list")
        if not (0 <= row.get("shard", -1) < NUM_SHARDS):
            errors.append(f"{pid}: shard {row.get('shard')} out of range")
        if not row.get("ingredientNames") and pct is None:
            warnings.append(f"{pid}: no ingredients and no protein figure")

    return errors, warnings


def main() -> int:
    if not SOURCE.exists():
        print(f"missing source file: {SOURCE}", file=sys.stderr)
        print("run build_dataset_supplements.py first (see docs/full-supplement-dataset.md)", file=sys.stderr)
        return 1

    writer = ShardWriter(SHARD_DIR, NUM_SHARDS)
    index: list[dict[str, Any]] = []
    generated = None
    source_citation = None
    licence = None
    unmapped_types: set[str] = set()

    print(f"streaming {SOURCE} ...", file=sys.stderr)
    with SOURCE.open("rb") as handle:
        # Dataset header fields sit alongside the (huge) products array; grab
        # them from a cheap top-level pass rather than re-opening the file.
        handle.seek(0)
        parser = ijson.parse(handle)
        for prefix, event, value in parser:
            if prefix == "generated":
                generated = value
            elif prefix == "source_citation":
                source_citation = value
            elif prefix == "licence":
                licence = value
            elif prefix == "products":
                break

    all_ingredient_names: set[str] = set()
    all_brands: set[str] = set()

    n = 0
    with SOURCE.open("rb") as handle:
        for raw in ijson.items(handle, "products.item"):
            n += 1
            product = Product.model_validate(raw)
            product_type = raw.get("product_type")
            category = PRODUCT_TYPE_TO_CATEGORY.get(product_type or "")
            if category is None:
                unmapped_types.add(product_type or "(none)")
                category = UNCATEGORIZED
            shard = product.dsld_id % NUM_SHARDS

            writer.write(shard, enrich(product, category))
            row = index_row(product, category, shard)
            index.append(row)
            all_brands.add(row["brand"])
            all_ingredient_names.update(row["ingredientNames"])

            if n % 10_000 == 0:
                print(f"  {n:,} products processed", file=sys.stderr)

    writer.close()
    print(f"streamed {n:,} products into {NUM_SHARDS} shards", file=sys.stderr)

    if unmapped_types:
        print(
            f"\nERROR: {len(unmapped_types)} unrecognised product_type value(s) not in "
            f"PRODUCT_TYPE_TO_CATEGORY: {sorted(unmapped_types)}",
            file=sys.stderr,
        )
        print(
            "Add them explicitly rather than letting them fall into 'uncategorized' silently.",
            file=sys.stderr,
        )
        return 1

    errors, warnings = check_quality(index)
    if warnings:
        print(f"\ndata quality: {len(warnings):,} warning(s) (upstream gaps, not blocking)", file=sys.stderr)
        for line in warnings[:5]:
            print(f"  - {line}", file=sys.stderr)
        if len(warnings) > 5:
            print(f"  - ... and {len(warnings) - 5:,} more", file=sys.stderr)

    if errors:
        print(f"\nDATA QUALITY GATE FAILED - {len(errors):,} error(s):", file=sys.stderr)
        for line in errors[:40]:
            print(f"  {line}", file=sys.stderr)
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40:,} more", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (OUT_DIR / "meta.json").write_text(
        json.dumps(
            {
                "generated": generated,
                "sourceCitation": source_citation,
                "licence": licence,
                "productCount": len(index),
                "shardCount": NUM_SHARDS,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # Autocomplete option lists for the ingredient/brand filters. Computed
    # here, once, rather than by scanning all ~117,800 index rows in the
    # browser on every load - building two ~100k-entry Sets client-side from
    # per-row arrays blocked the main thread for tens of seconds in testing.
    # This is the same principle as protein_pct_by_weight and allergens_all:
    # an aggregate over the whole corpus belongs in the batch build, not in a
    # React render.
    (OUT_DIR / "facets.json").write_text(
        json.dumps(
            {
                "ingredientNames": sorted(all_ingredient_names, key=str.casefold),
                "brands": sorted(all_brands, key=str.casefold),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    index_size = (OUT_DIR / "index.json").stat().st_size
    facets_size = (OUT_DIR / "facets.json").stat().st_size
    print(f"\nwrote {OUT_DIR / 'index.json'} ({index_size / 1_000_000:.1f} MB, {len(index):,} products)")
    print(f"wrote {NUM_SHARDS} shard files under {SHARD_DIR}")
    print(f"wrote {OUT_DIR / 'meta.json'}")
    print(
        f"wrote {OUT_DIR / 'facets.json'} ({facets_size / 1_000_000:.1f} MB, "
        f"{len(all_ingredient_names):,} ingredients, {len(all_brands):,} brands)"
    )
    print("data quality gate: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
