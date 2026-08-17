"""
Data model.

One design decision drives the whole file: `Trust` separates *verified
third-party certification* from *claims the manufacturer printed about itself*.

A label saying "manufactured in our FDA registered facility" is a claim about a
mailing address. NSF Certified for Sport means an independent lab tested every
batch against 280+ banned substances. Both appear on packaging in similar
typefaces and consumers read them as equivalent. They are not, and collapsing
them into one "certified" boolean would reproduce exactly the confusion this
project exists to correct.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Trust signals
# ---------------------------------------------------------------------------


class CertScope(str, Enum):
    """What a certification actually covers. The differentiator."""

    BANNED_SUBSTANCES_EVERY_BATCH = "banned_substances_every_batch"
    LABEL_ACCURACY = "label_accuracy"
    CONTAMINANTS = "contaminants"
    PROCESS_ONLY = "process_only"


class Certifier(str, Enum):
    NSF_CERTIFIED_FOR_SPORT = "nsf_certified_for_sport"
    NSF_CONTENTS_CERTIFIED = "nsf_contents_certified"
    INFORMED_SPORT = "informed_sport"
    INFORMED_CHOICE = "informed_choice"
    USP_VERIFIED = "usp_verified"
    BSCG = "bscg"


#: What each certifier verifies. Sourced from certifier documentation - see
#: README. This table is the substance of the app's differentiation, so it
#: carries a source and gets reviewed rather than being edited casually.
CERT_SCOPES: dict[Certifier, set[CertScope]] = {
    Certifier.NSF_CERTIFIED_FOR_SPORT: {
        CertScope.BANNED_SUBSTANCES_EVERY_BATCH,
        CertScope.LABEL_ACCURACY,
        CertScope.CONTAMINANTS,
    },
    Certifier.NSF_CONTENTS_CERTIFIED: {
        CertScope.LABEL_ACCURACY,
        CertScope.CONTAMINANTS,
    },
    Certifier.INFORMED_SPORT: {CertScope.BANNED_SUBSTANCES_EVERY_BATCH},
    # Informed Choice samples from retail rather than testing every batch.
    Certifier.INFORMED_CHOICE: {CertScope.CONTAMINANTS},
    Certifier.USP_VERIFIED: {
        CertScope.LABEL_ACCURACY,
        CertScope.CONTAMINANTS,
        CertScope.PROCESS_ONLY,
    },
    Certifier.BSCG: {CertScope.BANNED_SUBSTANCES_EVERY_BATCH},
}


class Certification(BaseModel):
    certifier: Certifier
    scopes: set[CertScope] = Field(default_factory=set)
    #: Certifier lists never name products identically to DSLD. Below ~0.9 a
    #: human should look before this is shown to a user as verified.
    match_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_url: str = ""
    retrieved: str = ""

    def model_post_init(self, _ctx: object) -> None:
        if not self.scopes:
            self.scopes = set(CERT_SCOPES.get(self.certifier, set()))


class Trust(BaseModel):
    """
    Verified certifications vs. self-asserted claims. Never merge these.
    """

    certifications: list[Certification] = Field(default_factory=list)

    # --- claims the manufacturer printed. NOT verification. ---
    gmp_claimed: bool = False
    fda_registration_claimed: bool = False
    third_party_tested_claimed: bool = False
    dshea_disclaimer_present: bool = False

    @property
    def batch_tested_for_banned_substances(self) -> bool:
        """The single most meaningful filter in the app."""
        return any(
            CertScope.BANNED_SUBSTANCES_EVERY_BATCH in c.scopes
            for c in self.certifications
        )

    @property
    def label_accuracy_verified(self) -> bool:
        return any(CertScope.LABEL_ACCURACY in c.scopes for c in self.certifications)

    @property
    def has_independent_verification(self) -> bool:
        return bool(self.certifications)

    @property
    def implies_approval_without_verification(self) -> bool:
        """
        The pattern worth surfacing to users: a label leaning on FDA
        registration or GMP language while carrying no independent
        certification at all. Legal, common, and misleading.
        """
        return (
            self.fda_registration_claimed or self.gmp_claimed
        ) and not self.has_independent_verification


# ---------------------------------------------------------------------------
# Ingredients
# ---------------------------------------------------------------------------


class Category(str, Enum):
    """
    Decision-useful categories, layered over DSLD's coarser ones.

    DSLD tells us sucralose is "non-nutrient/non-botanical". True, and useless
    to someone avoiding artificial sweeteners.
    """

    PROTEIN_SOURCE = "protein_source"
    ARTIFICIAL_SWEETENER = "artificial_sweetener"
    NATURAL_SWEETENER = "natural_sweetener"
    ADDED_SUGAR = "added_sugar"
    THICKENER_EMULSIFIER = "thickener_emulsifier"
    FILLER_BULKING = "filler_bulking"
    DIGESTIVE_ENZYME = "digestive_enzyme"
    FLAVOUR_COLOUR = "flavour_colour"
    VITAMIN = "vitamin"
    MINERAL = "mineral"
    AMINO_ACID = "amino_acid"
    STIMULANT = "stimulant"
    ALLERGEN_SOURCE = "allergen_source"
    MACRO = "macro"
    OTHER = "other"


class Ingredient(BaseModel):
    name: str
    #: FDA Unique Ingredient Identifier. Present on many DSLD rows and the only
    #: reliable join key - names are a mess ("Sucralose" / "sucralose" /
    #: "Splenda(R)" are one substance and only the UNII knows it).
    unii: str | None = None
    dsld_category: str | None = None
    categories: set[Category] = Field(default_factory=set)
    quantity: float | None = None
    unit: str | None = None
    percent_dv: float | None = None
    #: DSLD nests ingredients (Total Fat > Saturated Fat). Depth is preserved
    #: because "contains soy lecithin" reads differently at depth 0 vs 2.
    depth: int = 0
    is_proprietary_blend: bool = False


# ---------------------------------------------------------------------------
# Macros
# ---------------------------------------------------------------------------


class Macros(BaseModel):
    """Per serving, as declared. `None` means not on the label."""

    calories: float | None = None
    protein_g: float | None = None
    total_fat_g: float | None = None
    saturated_fat_g: float | None = None
    cholesterol_mg: float | None = None
    total_carbs_g: float | None = None
    sugar_g: float | None = None
    added_sugar_g: float | None = None
    fibre_g: float | None = None
    sodium_mg: float | None = None
    calcium_mg: float | None = None
    potassium_mg: float | None = None

    @property
    def protein_per_calorie(self) -> float | None:
        """
        Protein density. The most useful derived number in the category, and
        the one that exposes products bulked out with carbs and fat.
        """
        if not self.calories or self.protein_g is None:
            return None
        return round(self.protein_g / self.calories, 4)

    def protein_pct_by_weight(self, serving_g: float | None) -> float | None:
        if not serving_g or self.protein_g is None:
            return None
        return round(100 * self.protein_g / serving_g, 1)


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


#: Serving units that denote a real mass, with their factor to grams.
#: Anything else - scoops, packets, capsules, tablespoons - is a count or a
#: volume and cannot be converted without knowing the product's density.
_SERVING_UNIT_TO_G: dict[str, float] = {
    "gram(s)": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "g": 1.0,
    "mg": 0.001,
    "mcg": 0.000001,
    "kg": 1000.0,
    "ounce(s)": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
    "oz": 28.3495,
}


class Serving(BaseModel):
    quantity: float | None = None
    #: DSLD stores a range for labels that say "1-2 scoops". `quantity` is the
    #: low end; the Nutrition Facts panel is often written for the high end.
    max_quantity: float | None = None
    unit: str | None = None
    note: str | None = None
    per_container: str | None = None

    def _to_grams(self, value: float | None) -> float | None:
        if value is None:
            return None
        factor = _SERVING_UNIT_TO_G.get((self.unit or "").strip().lower())
        if factor is None:
            return None
        return value * factor

    @property
    def grams(self) -> float | None:
        """
        Serving size in grams, or None when the label declares a serving in
        units that carry no mass ("1 Scoop", "1 Packet", "2 Capsules").

        This guard exists because dividing by a raw `quantity` regardless of
        unit produced percentages like 2800% protein by weight - 28 g of
        protein divided by "1 Scoop". A missing number is honest; an
        impossible one is not.
        """
        return self._to_grams(self.quantity)

    @property
    def grams_max(self) -> float | None:
        return self._to_grams(self.max_quantity)

    @property
    def is_mass_unit(self) -> bool:
        return (self.unit or "").strip().lower() in _SERVING_UNIT_TO_G


class NutrientPanelEntry(BaseModel):
    """
    A Nutrition Facts panel row that isn't one of Macros' named fields (e.g.
    iron, zinc, vitamin D) - declared nutrient content, not an added
    ingredient. Kept separate from `Ingredient` so panel data doesn't read as
    "this was added to the product," which is the wrong claim for a row that
    is just restating %DV of a naturally-occurring or fortified nutrient.
    """

    name: str
    quantity: float | None = None
    unit: str | None = None
    percent_dv: float | None = None


class Product(BaseModel):
    dsld_id: int
    brand: str
    name: str
    upc: str | None = None
    off_market: bool = False
    entry_date: str | None = None

    physical_state: str | None = None
    product_type: str | None = None
    serving: Serving = Field(default_factory=Serving)
    macros: Macros = Field(default_factory=Macros)
    ingredients: list[Ingredient] = Field(default_factory=list)
    other_ingredients: list[Ingredient] = Field(default_factory=list)
    nutrient_panel: list[NutrientPanelEntry] = Field(default_factory=list)

    #: Allergens the label explicitly declares ("Contains: Milk").
    allergens: list[str] = Field(default_factory=list)
    #: Allergens implied by the ingredient list (see taxonomy.detect_allergens).
    #: Populated because 44% of labels declare nothing at all, including ones
    #: whose ingredients read "Milk" and "Lactose" - trusting the declaration
    #: alone lets those through an "exclude milk" filter.
    allergens_detected: list[str] = Field(default_factory=list)
    target_groups: list[str] = Field(default_factory=list)
    trust: Trust = Field(default_factory=Trust)

    manufacturer: str | None = None
    manufacturer_country: str | None = None

    source: str = "DSLD"
    source_url: str | None = None

    # --- derived filters ---------------------------------------------------

    def has_category(self, category: Category) -> bool:
        return any(
            category in i.categories for i in self.ingredients + self.other_ingredients
        )

    # --- allergens ---------------------------------------------------------
    #
    # Three states, deliberately kept distinct. Collapsing "not declared" into
    # "free of" is the failure that let whey products through an exclude-milk
    # filter, and it fails in the direction that hurts someone.

    @property
    def allergens_all(self) -> list[str]:
        """Declared and detected, unioned. What a filter should act on."""
        return sorted(set(self.allergens) | set(self.allergens_detected))

    @property
    def allergen_declaration_missing(self) -> bool:
        """
        True when the label carries no allergen declaration at all. Such a
        product must never be presented as free of anything - the absence of
        a statement is not a statement of absence.
        """
        return not self.allergens

    @property
    def protein_pct_by_weight(self) -> float | None:
        """
        Protein as a percentage of serving weight, or None when no reliable
        figure can be derived. Always prefer this over calling
        `macros.protein_pct_by_weight(serving.quantity)`, which silently
        divides grams of protein by scoops.

        Three real failure modes in DSLD, handled in order:

        1. The serving is declared in a unit with no mass ("1 Scoop") -
           `serving.grams` is None and so is the result.
        2. The serving is a range ("1-2 scoops") and the Nutrition Facts panel
           was written for the *upper* bound, while DSLD stores the lower one
           as `quantity`. Dividing by the lower bound gives figures like 183%.
           So a basis is only accepted if it yields a physically possible
           number, and the max is tried next.
        3. The label is simply self-inconsistent - 88 g of protein declared in
           a 30 g serving, or a serving unit recorded as "mg" when the net
           contents say grams. No basis works, and the honest answer is None.
        """
        return next(
            (
                pct
                for basis in (self.serving.grams, self.serving.grams_max)
                if (pct := self.macros.protein_pct_by_weight(basis)) is not None
                and 0 < pct <= 100
            ),
            None,
        )

    @property
    def protein_pct_basis(self) -> str | None:
        """
        Which serving figure `protein_pct_by_weight` used - useful for
        surfacing "per max serving" in the UI and for auditing the data.
        """
        for name, basis in (("declared", self.serving.grams), ("max_serving", self.serving.grams_max)):
            pct = self.macros.protein_pct_by_weight(basis)
            if pct is not None and 0 < pct <= 100:
                return name
        return None

    @property
    def protein_sources(self) -> list[str]:
        return [
            i.name
            for i in self.ingredients
            if Category.PROTEIN_SOURCE in i.categories
        ]

    @property
    def has_artificial_sweetener(self) -> bool:
        return self.has_category(Category.ARTIFICIAL_SWEETENER)

    @property
    def has_proprietary_blend(self) -> bool:
        """
        A proprietary blend hides per-ingredient doses. It is the mechanism
        behind amino spiking, so it is a filter in its own right.
        """
        return any(
            i.is_proprietary_blend
            for i in self.ingredients + self.other_ingredients
        )

    @property
    def ingredient_count(self) -> int:
        return len(self.ingredients) + len(self.other_ingredients)


class Dataset(BaseModel):
    """A versioned snapshot. Attribution is required by DSLD's request."""

    generated: str
    source_citation: str = (
        "National Institutes of Health, Office of Dietary Supplements. "
        "Dietary Supplement Label Database. https://dsld.od.nih.gov/"
    )
    licence: str = "CC0 1.0 Universal (source data)"
    query: str = ""
    products: list[Product] = Field(default_factory=list)

    def summary(self) -> dict[str, object]:
        live = [p for p in self.products if not p.off_market]
        return {
            "total": len(self.products),
            "on_market": len(live),
            "brands": len({p.brand for p in self.products}),
            "with_certification": sum(
                1 for p in live if p.trust.has_independent_verification
            ),
            "batch_tested": sum(
                1 for p in live if p.trust.batch_tested_for_banned_substances
            ),
            "implies_approval_only": sum(
                1 for p in live if p.trust.implies_approval_without_verification
            ),
            "with_artificial_sweetener": sum(
                1 for p in live if p.has_artificial_sweetener
            ),
        }
