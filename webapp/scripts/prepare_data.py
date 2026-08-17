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

SOURCE = ROOT / "data" / "dataset_full.json"
DEST = ROOT / "webapp" / "src" / "data" / "products.json"


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

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(dataset))

    print(f"wrote {DEST} ({len(dataset['products'])} products, {missing} missing category)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
