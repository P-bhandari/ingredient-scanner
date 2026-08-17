"""
Allergen detection.

DSLD declares no allergens for 44% of this catalogue, including products whose
ingredient lists read "Milk" and "Lactose". Deriving allergens from ingredients
is therefore a safety feature, and the failure modes run in both directions:

  - missing a real allergen is the dangerous error
  - inventing one from a lookalike word (Lactobacillus, Coconut Milk,
    Galactose) makes the filter useless and erodes trust in the whole tool

Every name below is real - taken from the ingredient names in the live
dataset. No network, no API key.

    pytest -q
"""

from __future__ import annotations

import pytest

from labellens.schema import Ingredient, Product, Serving
from labellens.taxonomy import detect_allergens


# ---------------------------------------------------------------------------
# Must NOT fire — real names that merely look like allergens
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "Lactobacillus acidophilus",     # probiotic, not dairy
        "Bifidobacterium lactis Bl-04",  # probiotic, not dairy
        "Bifidobacterium animalis lactis",
        "Lactase",                       # enzyme, not a milk declaration
        "Galactose",                     # a sugar; contains "lactose" as a substring
        "Milk Thistle",                  # botanical
        "sunflower Lecithin",            # must not read as soy
        "Sunflower Oil",
    ],
)
def test_lookalikes_do_not_report_milk_or_soy(name: str) -> None:
    found = detect_allergens(name)
    assert "milk" not in found, f"{name!r} wrongly flagged as milk"
    assert "soy" not in found, f"{name!r} wrongly flagged as soy"


@pytest.mark.parametrize(
    "name",
    ["Coconut Milk", "Coconut Milk, Powder", "Coconut Cream", "Coconut Oil"],
)
def test_plant_milks_are_tree_nut_not_dairy(name: str) -> None:
    """
    Coconut is a tree nut under FDA labelling, and is emphatically not dairy.
    Reading "Coconut Milk" as milk would hide safe products from someone
    avoiding dairy.
    """
    found = detect_allergens(name)
    assert "milk" not in found
    assert "tree nut" in found


# ---------------------------------------------------------------------------
# Must fire — the dangerous direction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Whey Protein Isolate", "milk"),
        ("100% pure grass fed Whey Protein concentrate", "milk"),
        ("Micellar Casein", "milk"),
        ("Calcium Caseinate", "milk"),
        ("Sodium Caseinate", "milk"),
        ("Lactose", "milk"),
        ("Alpha Lactalbumin", "milk"),
        ("Beta Lactoglobulin", "milk"),
        ("Milk", "milk"),
        ("instant whole Milk powder", "milk"),
        ("ion exchange Whey (Milk) Protein isolate", "milk"),
        ("Soy Lecithin", "soy"),
        ("Soy Protein isolate", "soy"),
        ("Soybean Oil", "soy"),
        ("Peanut Flour", "peanut"),
        ("Fish Collagen Peptides", "fish"),
        ("Eggshell Membrane", "egg"),
        ("Chicken Egg Membrane Type 1,5,& 10", "egg"),
        ("Wheat Protein", "wheat"),
        ("Almond Butter", "tree nut"),
        ("Sesame Seed", "sesame"),
    ],
)
def test_real_allergens_are_detected(name: str, expected: str) -> None:
    assert expected in detect_allergens(name), f"{name!r} should report {expected}"


def test_wheat_implies_gluten_but_not_the_reverse() -> None:
    assert detect_allergens("Wheat flour") >= {"wheat", "gluten"}
    barley = detect_allergens("Barley Grass powder")
    assert "gluten" in barley
    assert "wheat" not in barley


def test_no_signal_returns_empty_not_a_guarantee() -> None:
    """An empty result means "nothing detected", never "certified free"."""
    assert detect_allergens("Xanthan Gum") == set()
    assert detect_allergens("") == set()


# ---------------------------------------------------------------------------
# The three-state model on Product
# ---------------------------------------------------------------------------


def _product(**kw) -> Product:
    base = dict(dsld_id=1, brand="B", name="N", serving=Serving())
    return Product(**{**base, **kw})


def test_allergens_all_unions_declared_and_detected() -> None:
    p = _product(allergens=["milk"], allergens_detected=["soy", "milk"])
    assert p.allergens_all == ["milk", "soy"]


def test_undeclared_allergen_is_still_caught_by_detection() -> None:
    """
    The exact production failure: a whey product with no allergen statement
    used to survive an "exclude milk" filter.
    """
    p = _product(
        ingredients=[Ingredient(name="Whey Protein Concentrate")],
        allergens=[],
        allergens_detected=["milk"],
    )
    assert p.allergens == []               # nothing declared
    assert "milk" in p.allergens_all       # but we know anyway
    assert p.allergen_declaration_missing is True


def test_declaration_missing_flag_distinguishes_silence_from_absence() -> None:
    declared = _product(allergens=["milk"])
    silent = _product(allergens=[])
    assert declared.allergen_declaration_missing is False
    assert silent.allergen_declaration_missing is True
