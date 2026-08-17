"""
Parser tests against a REAL DSLD payload.

The fixture is the unmodified structure of DSLD label 51157 (NutraBio 100%
Hydrolyzed Whey Protein), fetched from the live API. Testing against real data
rather than a payload I invented is the difference between verifying the parser
and verifying my assumptions about the parser.

No network, no API key.

    pytest -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from labellens.dsld import parse_label
from labellens.schema import CertScope, Category, Certification, Certifier, Trust
from labellens.taxonomy import categorise, looks_proprietary, normalise

FIXTURE = Path(__file__).parent / "fixtures" / "dsld_51157.json"


@pytest.fixture(scope="module")
def product():
    return parse_label(json.loads(FIXTURE.read_text()))


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_identity(product) -> None:
    assert product.dsld_id == 51157
    assert product.brand == "NutraBio"
    assert product.name == "100% Hydrolyzed Whey Protein Alpine Vanilla"
    assert product.upc == "6 49908 25541 1"
    assert product.off_market is False
    assert product.physical_state == "Powder"
    assert product.manufacturer == "NutraBio Labs, Inc."


def test_serving(product) -> None:
    assert product.serving.quantity == 32.5
    assert product.serving.unit == "Gram(s)"
    assert product.serving.note == "1 scoop"
    assert product.serving.per_container == "70"


# ---------------------------------------------------------------------------
# Macros — including unit normalisation, which is where bugs hide
# ---------------------------------------------------------------------------


def test_macros_extracted(product) -> None:
    m = product.macros
    assert m.calories == 120
    assert m.protein_g == 25
    assert m.total_fat_g == 1.5
    assert m.saturated_fat_g == 1
    assert m.total_carbs_g == 2
    assert m.sugar_g == 2


def test_mg_units_preserved(product) -> None:
    """Cholesterol/sodium/etc. are declared in mg and must stay in mg."""
    assert product.macros.cholesterol_mg == 15
    assert product.macros.sodium_mg == 60
    assert product.macros.calcium_mg == 15
    assert product.macros.potassium_mg == 20


def test_protein_density(product) -> None:
    # 25g protein in a 32.5g scoop
    assert product.macros.protein_pct_by_weight(product.serving.quantity) == 76.9
    assert product.macros.protein_per_calorie == pytest.approx(25 / 120, abs=1e-4)


def test_protein_density_handles_missing_data() -> None:
    from labellens.schema import Macros

    assert Macros().protein_per_calorie is None
    assert Macros(protein_g=25).protein_pct_by_weight(None) is None


# ---------------------------------------------------------------------------
# Ingredients and categorisation
# ---------------------------------------------------------------------------


def test_nested_ingredients_are_walked(product) -> None:
    """
    Sucralose and Xanthan Gum are nested two levels deep under Sodium in this
    label. A parser that only reads the top level misses them entirely — and
    they are exactly what a user filters on.
    """
    names = {i.name for i in product.ingredients}
    assert "Sucralose" in names
    assert "Xanthan Gum" in names
    assert "hydrolyzed Whey Protein" in names


def test_panel_rows_excluded_from_ingredients(product) -> None:
    """
    Nutrition Facts rows belong in `macros`, not the ingredient list. DSLD puts
    both in `ingredientRows`; we split them.
    """
    names = {i.name for i in product.ingredients}
    for panel_row in ("Calories", "Total Fat", "Protein", "Sodium", "Calcium"):
        assert panel_row not in names, f"{panel_row} is a panel row, not an ingredient"
    # ...but its value still made it into macros
    assert product.macros.sodium_mg == 60


def test_depth_recorded(product) -> None:
    """
    Sucralose sits nested under Sodium in this label — a DSLD data-entry
    artifact. Depth is preserved so nesting is inspectable.
    """
    by_name = {i.name: i for i in product.ingredients}
    assert by_name["Sucralose"].depth == 1
    assert by_name["hydrolyzed Whey Protein"].depth == 0


def test_protein_source_identified(product) -> None:
    assert "hydrolyzed Whey Protein" in product.protein_sources


def test_artificial_sweetener_flagged(product) -> None:
    """
    The headline case. DSLD calls sucralose "non-nutrient/non-botanical",
    which is true and useless. Our taxonomy has to do better.
    """
    assert product.has_artificial_sweetener is True


def test_unii_takes_priority_over_name() -> None:
    """Xanthan gum's UNII resolves without touching the name patterns."""
    assert categorise("Some Trade Name", unii="TTV12P4NEE") == {
        Category.THICKENER_EMULSIFIER
    }


def test_longest_pattern_wins() -> None:
    assert Category.PROTEIN_SOURCE in categorise("Whey Protein Isolate")
    assert Category.ALLERGEN_SOURCE in categorise("Whey Protein Isolate")
    # Pea protein is a protein source but not one of the major allergens
    assert Category.ALLERGEN_SOURCE not in categorise("Pea Protein Isolate")


def test_normalisation_strips_trademarks() -> None:
    assert normalise("Sucralose®") == "sucralose"
    assert normalise("Xanthan  Gum (thickener)") == "xanthan gum thickener"


def test_maltodextrin_is_both_filler_and_sugar() -> None:
    cats = categorise("Maltodextrin")
    assert Category.FILLER_BULKING in cats
    assert Category.ADDED_SUGAR in cats


def test_header_rows_excluded(product) -> None:
    """
    'Absolutely None' under otheringredients is label furniture with
    ingredientGroup 'Header', not an ingredient.
    """
    assert product.other_ingredients == []


# ---------------------------------------------------------------------------
# Proprietary blends
# ---------------------------------------------------------------------------


def test_proprietary_blend_detection() -> None:
    assert looks_proprietary("Proprietary Energy Blend")
    assert looks_proprietary("Anabolic Matrix")
    assert looks_proprietary("Recovery Complex")
    # An honest disclosure of named sources is not a proprietary blend
    assert not looks_proprietary("Protein Blend")
    assert not looks_proprietary("Whey Protein Isolate")


def test_this_label_has_no_proprietary_blend(product) -> None:
    assert product.has_proprietary_blend is False


# ---------------------------------------------------------------------------
# Trust — the part that matters most
# ---------------------------------------------------------------------------


def test_self_asserted_claims_parsed(product) -> None:
    """
    This label says 'FDA registered & inspected GMP facility' and prints an FDA
    registration number. Both are claims about a facility, not product approval.
    """
    assert product.trust.fda_registration_claimed is True
    assert product.trust.gmp_claimed is True
    assert product.trust.dshea_disclaimer_present is True


def test_claims_are_not_verification(product) -> None:
    """
    The whole thesis of the project, as an assertion.

    Despite prominent FDA and GMP language, this product has no independent
    certification recorded — so it must not read as verified.
    """
    assert product.trust.has_independent_verification is False
    assert product.trust.batch_tested_for_banned_substances is False
    assert product.trust.implies_approval_without_verification is True


def test_allergens_parsed(product) -> None:
    assert "milk" in product.allergens


def test_free_from_claims_not_read_as_allergens(product) -> None:
    """'Soy Free, Gluten Free' must not register soy or gluten as present."""
    assert "soy" not in product.allergens
    assert "gluten" not in product.allergens


# ---------------------------------------------------------------------------
# Certification scope model
# ---------------------------------------------------------------------------


def test_cert_scopes_autopopulate() -> None:
    cert = Certification(certifier=Certifier.NSF_CERTIFIED_FOR_SPORT)
    assert CertScope.BANNED_SUBSTANCES_EVERY_BATCH in cert.scopes
    assert CertScope.LABEL_ACCURACY in cert.scopes


def test_usp_does_not_cover_banned_substances() -> None:
    """
    The distinction the app exists to make. USP Verified is strong on label
    accuracy and silent on banned substances.
    """
    trust = Trust(certifications=[Certification(certifier=Certifier.USP_VERIFIED)])
    assert trust.label_accuracy_verified is True
    assert trust.batch_tested_for_banned_substances is False
    assert trust.has_independent_verification is True


def test_nsf_for_sport_covers_banned_substances() -> None:
    trust = Trust(
        certifications=[Certification(certifier=Certifier.NSF_CERTIFIED_FOR_SPORT)]
    )
    assert trust.batch_tested_for_banned_substances is True


def test_certification_suppresses_misleading_flag() -> None:
    """Real certification means the 'implies approval' warning goes away."""
    trust = Trust(
        fda_registration_claimed=True,
        certifications=[Certification(certifier=Certifier.INFORMED_SPORT)],
    )
    assert trust.implies_approval_without_verification is False
