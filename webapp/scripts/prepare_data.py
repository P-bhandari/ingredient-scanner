"""
Prepares data/dataset_full.json for the webapp.

The canonical Product schema (labellens/schema.py) has no `category` field --
whey/plant/pea/casein/collagen only ever existed as an in-memory grouping
inside build_dataset_full.py's candidate selection. The webapp needs it for
category nav and filtering, so this script re-derives that mapping (cheap --
it replays from the on-disk DSLD response cache, no network calls) and joins
it onto each product before writing the webapp's copy of the data.

Run this after every `python build_dataset_full.py` re-pull, as part of the
same refresh cycle -- see docs/webapp-prd.md #8.

    python webapp/scripts/prepare_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from build_dataset_full import build_selection  # noqa: E402
from labellens.schema import Product  # noqa: E402

SOURCE = ROOT / "data" / "dataset_full.json"
DEST = ROOT / "webapp" / "src" / "data" / "products.json"


def check_quality(products: list[dict]) -> tuple[list[str], list[str]]:
    """
    Gate between the pipeline and the site.

    Errors are things we would be *asserting falsely* to a user - an
    impossible percentage, a missing category. Those fail the build, because
    publishing a fabricated number is worse than publishing nothing.

    Warnings are things the upstream data genuinely lacks. DSLD has records
    with no ingredient list at all; we can report that but not invent one, so
    it must not block a release.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for p in products:
        pid = f"{p['dsld_id']} ({p.get('brand', '?')})"

        pct = p.get("protein_pct_by_weight")
        if pct is not None and not (0 < pct <= 100):
            errors.append(f"{pid}: protein_pct_by_weight={pct} outside 0-100")

        if not p.get("category"):
            errors.append(f"{pid}: no category assigned")

        for field in ("allergens", "allergens_detected"):
            if not isinstance(p.get(field), list):
                errors.append(f"{pid}: {field} missing or not a list")

        unit = (p.get("serving") or {}).get("unit")
        if unit is not None and not isinstance(unit, str):
            errors.append(f"{pid}: serving unit is not a string ({unit!r})")

        if not p.get("ingredients") and not p.get("other_ingredients"):
            warnings.append(f"{pid}: no ingredient data in the source label")
        if pct is None:
            warnings.append(f"{pid}: protein % not derivable (non-mass or inconsistent serving)")

    return errors, warnings


def main() -> int:
    selection = build_selection()
    id_to_category = {item["id"]: cat for cat, items in selection.items() for item in items}

    dataset = json.loads(SOURCE.read_text())
    missing = 0
    for product in dataset["products"]:
        category = id_to_category.get(product["dsld_id"])
        if category is None:
            missing += 1
        product["category"] = category or "other"

        # Precompute the unit-aware figure so the client never has to guess
        # what "1 Scoop" weighs. None means "not comparable", not zero.
        model = Product.model_validate(product)
        product["protein_pct_by_weight"] = model.protein_pct_by_weight
        product["protein_pct_basis"] = model.protein_pct_basis
        product["serving_grams"] = model.serving.grams
        product["allergens_all"] = model.allergens_all
        product["allergen_declaration_missing"] = model.allergen_declaration_missing

    errors, warnings = check_quality(dataset["products"])

    if warnings:
        print(f"data quality: {len(warnings)} warning(s) (upstream gaps, not blocking)")
        for line in warnings[:5]:
            print(f"  - {line}")
        if len(warnings) > 5:
            print(f"  - ... and {len(warnings) - 5} more")

    if errors:
        print(f"\nDATA QUALITY GATE FAILED - {len(errors)} error(s):", file=sys.stderr)
        for line in errors[:40]:
            print(f"  {line}", file=sys.stderr)
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more", file=sys.stderr)
        return 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(dataset))

    print(f"wrote {DEST} ({len(dataset['products'])} products, {missing} missing category)")
    print(f"data quality gate: PASSED ({len(dataset['products'])} products checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
