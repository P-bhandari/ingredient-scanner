"""
Serving units and protein density.

The site displayed "2500% protein by weight" because the old calculation
divided grams of protein by the serving *quantity* while ignoring the serving
*unit* — 25 g of protein over "1 Scoop". Every case below is taken from a real
DSLD record that produced a wrong number.

    pytest -q
"""

from __future__ import annotations

import pytest

from labellens.schema import Macros, Product, Serving


def _p(quantity, unit, protein, max_quantity=None) -> Product:
    return Product(
        dsld_id=1,
        brand="B",
        name="N",
        serving=Serving(quantity=quantity, max_quantity=max_quantity, unit=unit),
        macros=Macros(protein_g=protein),
    )


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "quantity,unit,expected",
    [
        (32.5, "Gram(s)", 32.5),
        (32.5, "g", 32.5),
        (1, "Ounce(s)", 28.3495),
        (1000, "mg", 1.0),
        (1, "kg", 1000.0),
    ],
)
def test_mass_units_convert_to_grams(quantity, unit, expected) -> None:
    assert Serving(quantity=quantity, unit=unit).grams == pytest.approx(expected)


@pytest.mark.parametrize(
    "unit",
    ["Scoop(s)", "Level Scoop(s)", "Packet(s)", "Tablet(s)", "Vegetable Capsule(s)",
     "Liquid Glycerin Capsule(s)", "Tbsp", None],
)
def test_countable_and_volume_units_have_no_mass(unit) -> None:
    """
    A scoop has no defined weight. Returning None is the honest answer; the
    old code returned a number, and that number was nonsense.
    """
    s = Serving(quantity=1, unit=unit)
    assert s.grams is None
    assert s.is_mass_unit is False


# ---------------------------------------------------------------------------
# Protein % — the three real failure modes
# ---------------------------------------------------------------------------


def test_normal_case_uses_the_declared_serving() -> None:
    p = _p(32.5, "Gram(s)", 25)          # NutraBio whey, label 51157
    assert p.protein_pct_by_weight == 76.9
    assert p.protein_pct_basis == "declared"


def test_scoop_serving_yields_no_percentage_rather_than_2500() -> None:
    """BPT Proteinification: 28 g protein, serving declared as "1 Scoop"."""
    p = _p(1, "Scoop(s)", 28)
    assert p.protein_pct_by_weight is None
    assert p.protein_pct_basis is None


def test_range_serving_falls_back_to_the_upper_bound() -> None:
    """
    Bulletproof Collagen (label 213909): DSLD stores minQuantity=12 for a
    "1-2 scoops" serving while the panel describes 24 g. 22/12 = 183% is
    impossible, so the max is the intended basis.
    """
    p = _p(12, "Gram(s)", 22, max_quantity=24)
    assert p.protein_pct_by_weight == pytest.approx(91.7, abs=0.1)
    assert p.protein_pct_basis == "max_serving"


def test_self_inconsistent_label_yields_none() -> None:
    """
    Body Attack (label 334151): 88 g of protein declared in a 30 g serving.
    No basis makes that possible, so we publish nothing rather than a
    fabricated figure.
    """
    p = _p(30, "Gram(s)", 88, max_quantity=30)
    assert p.protein_pct_by_weight is None


def test_wrong_unit_in_source_data_yields_none() -> None:
    """
    NutraBio Performance (label 329454): serving unit recorded as "mg" when
    the net contents say 29.8 grams. 25 g / 0.0298 g = 83,892%.
    """
    p = _p(29.8, "mg", 25)
    assert p.protein_pct_by_weight is None


def test_missing_protein_or_serving_is_not_an_error() -> None:
    assert _p(30, "Gram(s)", None).protein_pct_by_weight is None
    assert _p(None, "Gram(s)", 25).protein_pct_by_weight is None


@pytest.mark.parametrize(
    "quantity,unit,protein,max_quantity",
    [
        (1, "Scoop(s)", 28, None),      # no mass unit
        (30, "Gram(s)", 88, 30),        # self-inconsistent label
        (29.8, "mg", 25, None),         # wrong unit upstream
        (12, "Gram(s)", 22, 24),        # range serving
        (32.5, "Gram(s)", 25, None),    # ordinary case
        (1, "Ounce(s)", 25, None),      # 25 g in 28.35 g
    ],
)
def test_percentage_can_never_exceed_100(quantity, unit, protein, max_quantity) -> None:
    """The invariant the data-quality gate also enforces on the built dataset."""
    pct = _p(quantity, unit, protein, max_quantity).protein_pct_by_weight
    assert pct is None or 0 < pct <= 100
