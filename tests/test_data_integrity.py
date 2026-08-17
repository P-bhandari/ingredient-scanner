"""
Invariants on the built dataset the site actually serves.

The unit tests prove the logic is right; this proves the *shipped data* is
right. Every assertion here corresponds to something that reached users:
impossible percentages, dairy products passing an "exclude milk" filter,
products with no category.

Runs against webapp/src/data/products.json, so it fails if someone reruns the
pipeline against changed upstream data and a regression slips in. Skips
cleanly when that file hasn't been generated yet.

    pytest -q
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

DATA = Path(__file__).parent.parent / "webapp" / "src" / "data" / "products.json"

pytestmark = pytest.mark.skipif(
    not DATA.exists(),
    reason="run `python webapp/scripts/prepare_data.py` to generate the webapp dataset",
)


@pytest.fixture(scope="module")
def products() -> list[dict]:
    return json.loads(DATA.read_text())["products"]


def test_dataset_is_not_empty(products) -> None:
    assert len(products) > 300


def test_no_impossible_protein_percentage(products) -> None:
    """The 2500% bug, asserted against real shipped data."""
    bad = [
        (p["dsld_id"], p["brand"], p["protein_pct_by_weight"])
        for p in products
        if p.get("protein_pct_by_weight") is not None
        and not (0 < p["protein_pct_by_weight"] <= 100)
    ]
    assert bad == [], f"{len(bad)} products with impossible protein %: {bad[:5]}"


def test_protein_percentage_is_derivable_for_most_products(products) -> None:
    """
    Guards the opposite regression: a stricter rule that quietly discards the
    figure for everything would also pass the test above.
    """
    derivable = sum(1 for p in products if p.get("protein_pct_by_weight") is not None)
    assert derivable / len(products) > 0.85


def test_every_product_has_a_category(products) -> None:
    assert [p["dsld_id"] for p in products if not p.get("category")] == []


def test_every_product_has_both_allergen_fields(products) -> None:
    for p in products:
        assert isinstance(p.get("allergens"), list), p["dsld_id"]
        assert isinstance(p.get("allergens_detected"), list), p["dsld_id"]
        assert isinstance(p.get("allergens_all"), list), p["dsld_id"]


_DAIRY = re.compile(r"\b(whey|casein|caseinate|lactalbumin|lactoglobulin)|\blactose", re.I)


def test_no_dairy_product_passes_an_exclude_milk_filter(products) -> None:
    """
    The production safety bug: 45 products containing whey, casein or lactose
    survived "exclude milk" because DSLD declared no allergens for them.
    """
    leaks = []
    for p in products:
        if "milk" in p["allergens_all"]:
            continue
        names = [i["name"] for i in p["ingredients"] + p["other_ingredients"]]
        hits = [n for n in names if _DAIRY.search(n)]
        if hits:
            leaks.append((p["dsld_id"], p["brand"], hits[:2]))
    assert leaks == [], f"{len(leaks)} dairy products would pass an exclude-milk filter: {leaks[:5]}"


def test_dairy_named_products_do_not_pass_an_exclude_milk_filter(products) -> None:
    """
    The second leak, found by cross-checking the rendered grid: products that
    disclose nothing and hide the source behind an opaque "Protein Blend",
    while being named "100% Casein Protein". The name is evidence too.
    """
    leaks = [
        (p["dsld_id"], p["name"])
        for p in products
        if "milk" not in p["allergens_all"] and _DAIRY.search(p["name"])
    ]
    assert leaks == [], f"{len(leaks)} dairy-named products pass exclude-milk: {leaks[:5]}"


def test_whey_and_casein_categories_are_treated_as_dairy(products) -> None:
    """
    A whey or casein product that survives an exclude-milk filter is a safety
    failure regardless of how sparse its label is.
    """
    leaks = [
        (p["dsld_id"], p["category"], p["name"])
        for p in products
        if p["category"] in ("whey", "casein") and "milk" not in p["allergens_all"]
    ]
    assert leaks == [], f"{len(leaks)} whey/casein products pass exclude-milk: {leaks[:5]}"


def test_allergen_detection_did_not_flag_everything(products) -> None:
    """
    An over-eager detector that marked every product as containing everything
    would also pass the leak test. Milk should be common in a protein-powder
    catalogue but nowhere near universal.
    """
    with_milk = sum(1 for p in products if "milk" in p["allergens_all"])
    assert 0.2 < with_milk / len(products) < 0.8


def test_serving_units_are_strings_or_absent(products) -> None:
    for p in products:
        unit = (p.get("serving") or {}).get("unit")
        assert unit is None or isinstance(unit, str), p["dsld_id"]


def test_no_product_is_entirely_without_ingredient_data(products) -> None:
    """
    Known upstream gap rather than a hard failure - DSLD has records with no
    ingredient list. Pinned so the number can't grow unnoticed.
    """
    empty = [p["dsld_id"] for p in products if not p["ingredients"] and not p["other_ingredients"]]
    assert len(empty) <= 1, f"products with no ingredient data at all: {empty}"


def test_certifications_carry_scopes(products) -> None:
    """A certification with no scope would render as a meaningless badge."""
    for p in products:
        for cert in p["trust"]["certifications"]:
            assert cert["scopes"], f"{p['dsld_id']}: {cert['certifier']} has no scopes"
