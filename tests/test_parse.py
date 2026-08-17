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


def test_dedicated_free_of_statement_overrides_facility_warning() -> None:
    """
    Real statements from live label 205264: a "Does NOT Contain" declaration
    naming several allergens in one negative claim must win over a vaguer
    "manufactured in a facility that also processes ..." caution that names
    the same allergens. Only the product's own "Contains: Milk" should
    survive.
    """
    raw = {
        "id": 205264,
        "brandName": "Extreme Edge",
        "fullName": "100% Pure Whey Protein Isolate",
        "statements": [
            {"type": "Precautions re: Allergies", "notes": "Contains: Milk"},
            {
                "type": "Formulation re: Does NOT Contain",
                "notes": "Free of Egg, Fish, Crustacean Shellfish, Tree Nuts, Peanuts, "
                "Wheat and Soybeans.\nAlso Free of Yeast, Gluten, Barley and Rice.",
            },
            {
                "type": "Precautions re: Allergies",
                "notes": "Allergen Warning: Manufactured in a facility that processes "
                "products containing milk, eggs, soybeans, wheat, shellfish, fish oil, "
                "tree nuts and peanut flavor.",
            },
        ],
    }
    p = parse_label(raw)
    assert p.allergens == ["milk"]


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


# ---------------------------------------------------------------------------
# Certification detection from label statements
#
# parse_label() must actually populate `trust.certifications` when a real
# seal is printed on the label, not just detect self-asserted claims. Text
# below is taken verbatim from live DSLD labels (205264, 67269).
# ---------------------------------------------------------------------------


def test_nsf_certified_for_sport_detected_from_statements() -> None:
    raw = {
        "id": 205264,
        "brandName": "Extreme Edge",
        "fullName": "100% Pure Whey Protein Isolate",
        "statements": [
            {"type": "Seals/Symbols", "notes": "NSF\nCertified for Sport"},
            {
                "type": "General Statements: All Other Content",
                "notes": "Tested Certified Safer with NSF Certified for Sport "
                "Product tested for 200+ banned substances.",
            },
        ],
    }
    p = parse_label(raw)
    assert p.trust.has_independent_verification is True
    assert p.trust.batch_tested_for_banned_substances is True
    # Two statements mention the same seal; must not double-count it.
    assert len(p.trust.certifications) == 1
    assert p.trust.certifications[0].certifier == Certifier.NSF_CERTIFIED_FOR_SPORT
    assert p.trust.certifications[0].source_url == "https://dsld.od.nih.gov/label/205264"


def test_informed_choice_detected_from_statements() -> None:
    raw = {
        "id": 67269,
        "brandName": "GNC Pro Performance",
        "fullName": "100% Casein Protein Chocolate Supreme",
        "statements": [
            {"type": "Seals/Symbols", "notes": "Informed-choice.org Trusted by sport"},
        ],
    }
    p = parse_label(raw)
    assert p.trust.has_independent_verification is True
    assert p.trust.certifications[0].certifier == Certifier.INFORMED_CHOICE
    # Informed Choice samples from retail rather than testing every batch.
    assert p.trust.batch_tested_for_banned_substances is False


# ---------------------------------------------------------------------------
# Nutrition-panel rows that aren't in Macros (iron, vitamin D, ...)
#
# DSLD sometimes represents a product's entire ingredientRows as just the
# Nutrition Facts panel (seen live on label 205264 - an "Extreme Edge" whey
# isolate whose only "ingredients" were Calories/Protein/Iron/Phosphorus/
# Magnesium/Copper/Chloride, with the real ingredients - cocoa, flavor,
# lecithin, stevia - filed separately under otheringredients). A plain
# "Iron" row is declared nutrient content, not something added to the tub,
# and must not read as an ingredient.
# ---------------------------------------------------------------------------


def test_panel_micronutrients_excluded_from_ingredients_and_captured() -> None:
    raw = {
        "id": 205264,
        "brandName": "Extreme Edge",
        "fullName": "100% Pure Whey Protein Isolate",
        "ingredientRows": [
            {"name": "Protein", "category": "protein", "quantity": [{"quantity": 26, "unit": "Gram(s)"}]},
            {"name": "Iron", "category": "mineral", "quantity": [{"quantity": 0.5, "unit": "mg"}]},
            {"name": "Magnesium", "category": "mineral", "quantity": [{"quantity": 30, "unit": "mg"}]},
        ],
    }
    p = parse_label(raw)
    names = {i.name for i in p.ingredients}
    assert "Iron" not in names
    assert "Magnesium" not in names
    assert p.macros.protein_g == 26

    panel_names = {n.name: n for n in p.nutrient_panel}
    assert panel_names["Iron"].quantity == 0.5
    assert panel_names["Iron"].unit == "mg"
    assert panel_names["Magnesium"].quantity == 30


def test_named_mineral_ingredient_form_still_counts_as_ingredient() -> None:
    """"Zinc Oxide" is a specific ingredient form actually added to the
    product - unlike a bare "Zinc" panel row, it must stay an ingredient."""
    raw = {
        "id": 1,
        "brandName": "Brand",
        "fullName": "Product",
        "ingredientRows": [
            {"name": "Zinc Oxide", "category": "mineral", "uniiCode": "SOI2LOH54Z"},
        ],
    }
    p = parse_label(raw)
    assert "Zinc Oxide" in {i.name for i in p.ingredients}
    assert p.nutrient_panel == []


def test_sucralose_nested_under_sodium_still_an_ingredient(product) -> None:
    """Regression guard: the panel-nutrient exclusion must not accidentally
    swallow real ingredients that happen to be nested under a panel row due
    to DSLD's data-entry quirks (see test_depth_recorded)."""
    names = {i.name for i in product.ingredients}
    assert "Sucralose" in names


def test_claims_without_a_seal_still_carry_no_certification() -> None:
    """FDA/GMP language alone must not be mistaken for a certification."""
    raw = {
        "id": 1,
        "brandName": "Brand",
        "fullName": "Product",
        "statements": [
            {"type": "General Statements", "notes": "FDA registered and inspected GMP facility"},
        ],
    }
    p = parse_label(raw)
    assert p.trust.certifications == []
    assert p.trust.implies_approval_without_verification is True
