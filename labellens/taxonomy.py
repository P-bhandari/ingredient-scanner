"""
Ingredient -> category mapping.

DSLD gives a coarse category per ingredient row. Useful, but not what people
filter on: it will tell you sucralose is "non-nutrient/non-botanical", which is
true and no help at all to someone avoiding artificial sweeteners.

This module layers a decision-useful taxonomy on top.

Matching order, and it matters:

  1. UNII  - FDA's Unique Ingredient Identifier. Authoritative. "Sucralose",
             "sucralose" and "Splenda(R)" are one substance and only the
             identifier knows that.
  2. Exact normalised name
  3. Substring rules, longest pattern first

Everything unmatched lands in `unmapped()` rather than being silently dropped,
because a filter that quietly misses ingredients is worse than no filter.
"""

from __future__ import annotations

import re
from collections import Counter

from .schema import Category

# ---------------------------------------------------------------------------
# UNII -> categories. Authoritative tier.
#
# UNII codes observed in DSLD label data. Extend deliberately: each entry is a
# claim that a specific substance belongs in a specific bucket, and users will
# filter on it.
# ---------------------------------------------------------------------------

UNII_MAP: dict[str, set[Category]] = {
    "TTV12P4NEE": {Category.THICKENER_EMULSIFIER},  # Xanthan gum
    "C151H8M554": {Category.ADDED_SUGAR},  # Sugar
    "SY7Q814VUP": {Category.MINERAL},  # Calcium
    "9NEZ333N27": {Category.MINERAL},  # Sodium
    "RWP5GA015D": {Category.MINERAL},  # Potassium
    "3K9958V90M": {Category.STIMULANT},  # Caffeine
    "96K6UQ3ZD4": {Category.ARTIFICIAL_SWEETENER},  # Aspartame
    "0RE8K4LNJS": {Category.ARTIFICIAL_SWEETENER},  # Acesulfame potassium
    "3SC8QI2R23": {Category.NATURAL_SWEETENER},  # Erythritol
    "VO1DPX3X2Q": {Category.NATURAL_SWEETENER},  # Xylitol
}


# ---------------------------------------------------------------------------
# Name patterns. Fallback tier. Longest pattern wins.
# ---------------------------------------------------------------------------

NAME_PATTERNS: dict[str, set[Category]] = {
    # -- protein sources --------------------------------------------------
    "whey protein isolate": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "whey protein concentrate": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "hydrolyzed whey protein": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "hydrolysed whey protein": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "whey protein": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "milk protein isolate": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "micellar casein": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "calcium caseinate": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "casein": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "pea protein isolate": {Category.PROTEIN_SOURCE},
    "pea protein": {Category.PROTEIN_SOURCE},
    "brown rice protein": {Category.PROTEIN_SOURCE},
    "rice protein": {Category.PROTEIN_SOURCE},
    "soy protein isolate": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "soy protein": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "hemp protein": {Category.PROTEIN_SOURCE},
    "pumpkin seed protein": {Category.PROTEIN_SOURCE},
    "egg white protein": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "egg albumen": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "collagen peptide": {Category.PROTEIN_SOURCE},
    "collagen": {Category.PROTEIN_SOURCE},
    "beef protein": {Category.PROTEIN_SOURCE},
    # -- artificial sweeteners --------------------------------------------
    "sucralose": {Category.ARTIFICIAL_SWEETENER},
    "aspartame": {Category.ARTIFICIAL_SWEETENER},
    "acesulfame potassium": {Category.ARTIFICIAL_SWEETENER},
    "acesulfame-k": {Category.ARTIFICIAL_SWEETENER},
    "saccharin": {Category.ARTIFICIAL_SWEETENER},
    "neotame": {Category.ARTIFICIAL_SWEETENER},
    "advantame": {Category.ARTIFICIAL_SWEETENER},
    # -- natural / sugar alcohols -----------------------------------------
    "stevia": {Category.NATURAL_SWEETENER},
    "steviol glycoside": {Category.NATURAL_SWEETENER},
    "rebaudioside": {Category.NATURAL_SWEETENER},
    "monk fruit": {Category.NATURAL_SWEETENER},
    "luo han guo": {Category.NATURAL_SWEETENER},
    "erythritol": {Category.NATURAL_SWEETENER},
    "xylitol": {Category.NATURAL_SWEETENER},
    "maltitol": {Category.NATURAL_SWEETENER},
    "sorbitol": {Category.NATURAL_SWEETENER},
    "allulose": {Category.NATURAL_SWEETENER},
    # -- added sugars ------------------------------------------------------
    "cane sugar": {Category.ADDED_SUGAR},
    "corn syrup solids": {Category.ADDED_SUGAR, Category.FILLER_BULKING},
    "corn syrup": {Category.ADDED_SUGAR},
    "brown rice syrup": {Category.ADDED_SUGAR},
    "coconut sugar": {Category.ADDED_SUGAR},
    "sucrose": {Category.ADDED_SUGAR},
    "fructose": {Category.ADDED_SUGAR},
    "dextrose": {Category.ADDED_SUGAR, Category.FILLER_BULKING},
    "honey": {Category.ADDED_SUGAR},
    # maltodextrin: a carb filler more than a sweetener, and the classic
    # bulking agent in cheap powders. Both tags, deliberately.
    "maltodextrin": {Category.FILLER_BULKING, Category.ADDED_SUGAR},
    # -- thickeners / emulsifiers -----------------------------------------
    "xanthan gum": {Category.THICKENER_EMULSIFIER},
    "guar gum": {Category.THICKENER_EMULSIFIER},
    "gum arabic": {Category.THICKENER_EMULSIFIER},
    "acacia gum": {Category.THICKENER_EMULSIFIER},
    "cellulose gum": {Category.THICKENER_EMULSIFIER},
    "carrageenan": {Category.THICKENER_EMULSIFIER},
    "soy lecithin": {Category.THICKENER_EMULSIFIER, Category.ALLERGEN_SOURCE},
    "sunflower lecithin": {Category.THICKENER_EMULSIFIER},
    "lecithin": {Category.THICKENER_EMULSIFIER},
    "silicon dioxide": {Category.THICKENER_EMULSIFIER},
    "magnesium stearate": {Category.THICKENER_EMULSIFIER},
    # DSLD lists this as "Gum Acacia"; same substance as "Gum Arabic" above,
    # just reordered, so the existing pattern doesn't catch it.
    "gum acacia": {Category.THICKENER_EMULSIFIER},
    # -- fillers ------------------------------------------------------------
    "inulin": {Category.FILLER_BULKING},
    "rice flour": {Category.FILLER_BULKING},
    "oat flour": {Category.FILLER_BULKING},
    "corn starch": {Category.FILLER_BULKING},
    "soluble fiber": {Category.FILLER_BULKING},
    "insoluble fiber": {Category.FILLER_BULKING},
    # Salt's chemical name - DSLD lists both interchangeably across labels.
    "sodium chloride": {Category.FLAVOUR_COLOUR},
    # -- enzymes ------------------------------------------------------------
    "protease": {Category.DIGESTIVE_ENZYME},
    "lactase": {Category.DIGESTIVE_ENZYME},
    "bromelain": {Category.DIGESTIVE_ENZYME},
    "papain": {Category.DIGESTIVE_ENZYME},
    "amylase": {Category.DIGESTIVE_ENZYME},
    "aminogen": {Category.DIGESTIVE_ENZYME},
    "digezyme": {Category.DIGESTIVE_ENZYME},
    "alpha-galactosidase": {Category.DIGESTIVE_ENZYME},
    "lipase": {Category.DIGESTIVE_ENZYME},
    "cellulase": {Category.DIGESTIVE_ENZYME},
    # -- flavour / colour ---------------------------------------------------
    "natural flavor": {Category.FLAVOUR_COLOUR},
    "natural flavour": {Category.FLAVOUR_COLOUR},
    "artificial flavor": {Category.FLAVOUR_COLOUR},
    "artificial flavour": {Category.FLAVOUR_COLOUR},
    "natural and artificial flavor": {Category.FLAVOUR_COLOUR},
    "flavoring": {Category.FLAVOUR_COLOUR},
    "flavouring": {Category.FLAVOUR_COLOUR},
    "cocoa powder": {Category.FLAVOUR_COLOUR},
    "cocoa": {Category.FLAVOUR_COLOUR},
    "titanium dioxide": {Category.FLAVOUR_COLOUR},
    "red 40": {Category.FLAVOUR_COLOUR},
    "blue 1": {Category.FLAVOUR_COLOUR},
    "yellow 5": {Category.FLAVOUR_COLOUR},
    "yellow 6": {Category.FLAVOUR_COLOUR},
    "caramel color": {Category.FLAVOUR_COLOUR},
    "beet juice": {Category.FLAVOUR_COLOUR},
    "annatto": {Category.FLAVOUR_COLOUR},
    "salt": {Category.FLAVOUR_COLOUR},
    "sea salt": {Category.FLAVOUR_COLOUR},
    "vanilla": {Category.FLAVOUR_COLOUR},
    # -- stimulants ---------------------------------------------------------
    "caffeine": {Category.STIMULANT},
    "green tea extract": {Category.STIMULANT},
    "guarana": {Category.STIMULANT},
    # -- amino acids --------------------------------------------------------
    "leucine": {Category.AMINO_ACID},
    "isoleucine": {Category.AMINO_ACID},
    "valine": {Category.AMINO_ACID},
    "glutamine": {Category.AMINO_ACID},
    "taurine": {Category.AMINO_ACID},
    "creatine": {Category.AMINO_ACID},
    "glycine": {Category.AMINO_ACID},
    "arginine": {Category.AMINO_ACID},
    # -- minerals (mineral-form additives, distinct from the mineral panel
    #    rows themselves which are handled as macros in dsld.py) ------------
    "tricalcium phosphate": {Category.MINERAL},
    "dicalcium phosphate": {Category.MINERAL},
    "calcium phosphate": {Category.MINERAL},
    "dipotassium phosphate": {Category.MINERAL},
    "ferrous fumarate": {Category.MINERAL},
    "zinc oxide": {Category.MINERAL},
    "silica": {Category.MINERAL},
    "potassium chloride": {Category.MINERAL},
    "sodium gluconate": {Category.MINERAL},
    # -- vitamins -------------------------------------------------------------
    "vitamin d2": {Category.VITAMIN},
    "vitamin b12": {Category.VITAMIN},
    "sodium ascorbate": {Category.VITAMIN},
    "tocopherols": {Category.VITAMIN},
    "tocopherol": {Category.VITAMIN},
    # -- fats -----------------------------------------------------------------
    "medium chain triglycerides": {Category.OTHER},
    "sunflower oil": {Category.OTHER},
    "flax seed": {Category.OTHER},
    "diglycerides": {Category.THICKENER_EMULSIFIER},
    "monoglycerides": {Category.THICKENER_EMULSIFIER},
    # -- fillers / thickeners --------------------------------------------------
    "tapioca starch": {Category.FILLER_BULKING},
    "dextrin": {Category.FILLER_BULKING, Category.ADDED_SUGAR},
    "modified food starch": {Category.FILLER_BULKING},
    "cellulose gum": {Category.THICKENER_EMULSIFIER},
    "cellulose": {Category.FILLER_BULKING},
    "sodium carboxymethyl cellulose": {Category.THICKENER_EMULSIFIER},
    "vegetable stearate": {Category.THICKENER_EMULSIFIER},
    "stearic acid": {Category.THICKENER_EMULSIFIER},
    # -- fiber ------------------------------------------------------------------
    "oat bran": {Category.OTHER},
    "fructo-oligosaccharides": {Category.OTHER},
    # -- amino acids --------------------------------------------------------
    "l-proline": {Category.AMINO_ACID},
    "proline": {Category.AMINO_ACID},
    "l-lysine": {Category.AMINO_ACID},
    "lysine": {Category.AMINO_ACID},
    "l-glutamine": {Category.AMINO_ACID},
    # -- botanicals / flavour -------------------------------------------------
    "natural chocolate flavor": {Category.FLAVOUR_COLOUR},
    "natural raspberry flavor": {Category.FLAVOUR_COLOUR},
    "chocolate bean powder": {Category.FLAVOUR_COLOUR},
    "cucumber powder": {Category.OTHER},
    "spinach powder": {Category.OTHER},
    "chia": {Category.OTHER},
    "chicory": {Category.OTHER},
    "cinnamon": {Category.FLAVOUR_COLOUR},
    "grape seed extract": {Category.OTHER},
    # -- other, named for what they are rather than dumped silently --------
    "citric acid": {Category.OTHER},
    "hyaluronic acid": {Category.OTHER},
    "water": {Category.OTHER},
    "non-fat dry milk": {Category.ALLERGEN_SOURCE},
    "immunoglobulins": {Category.OTHER},
    "alpha lactalbumin": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "beta lactoglobulin": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    "beef broth powdered": {Category.PROTEIN_SOURCE},
    "turkey broth powdered": {Category.PROTEIN_SOURCE},
    "chicken broth powdered": {Category.PROTEIN_SOURCE},
    "whey": {Category.PROTEIN_SOURCE, Category.ALLERGEN_SOURCE},
    # -- macros -------------------------------------------------------------
    "calories": {Category.MACRO},
    "total fat": {Category.MACRO},
    "saturated fat": {Category.MACRO},
    "trans fat": {Category.MACRO},
    "cholesterol": {Category.MACRO},
    "total carbohydrate": {Category.MACRO},
    "dietary fiber": {Category.MACRO},
    "dietary fibre": {Category.MACRO},
    "protein": {Category.MACRO},
    "sugar": {Category.MACRO, Category.ADDED_SUGAR},
}

#: Longest-first so "whey protein isolate" beats "whey protein",
#: and "soy protein isolate" beats "protein".
_SORTED_PATTERNS: list[tuple[str, set[Category]]] = sorted(
    NAME_PATTERNS.items(), key=lambda kv: -len(kv[0])
)


# DSLD's own coarse category as a last resort.
DSLD_FALLBACK: dict[str, set[Category]] = {
    "protein": {Category.PROTEIN_SOURCE},
    "vitamin": {Category.VITAMIN},
    "mineral": {Category.MINERAL},
    "amino acid": {Category.AMINO_ACID},
    "fat": {Category.MACRO},
    "sugar": {Category.MACRO},
    "fiber": {Category.FILLER_BULKING},
    "enzyme": {Category.DIGESTIVE_ENZYME},
    "botanical": {Category.OTHER},
    "complex carbohydrate": {Category.OTHER},
    "non-nutrient/non-botanical": {Category.OTHER},
    "other": {Category.OTHER},
}


_PROPRIETARY = re.compile(
    r"\b(proprietary|blend|complex|matrix|formula)\b", re.IGNORECASE
)
_PUNCT = re.compile(r"[®™©\(\)\[\],\.]")
_WS = re.compile(r"\s+")

_unmapped: Counter[str] = Counter()


def normalise(name: str) -> str:
    """Lowercase, strip trademark symbols and punctuation, collapse spaces."""
    s = _PUNCT.sub(" ", name.lower())
    return _WS.sub(" ", s).strip()


def categorise(
    name: str, unii: str | None = None, dsld_category: str | None = None
) -> set[Category]:
    """
    UNII, then exact name, then substring, then DSLD's own category.

    Anything unmatched is recorded in `unmapped()` so gaps are visible instead
    of silently swallowed.
    """
    if unii and unii in UNII_MAP:
        return set(UNII_MAP[unii])

    norm = normalise(name)
    if not norm:
        return {Category.OTHER}

    if norm in NAME_PATTERNS:
        return set(NAME_PATTERNS[norm])

    for pattern, cats in _SORTED_PATTERNS:
        if pattern in norm:
            return set(cats)

    if dsld_category:
        key = dsld_category.lower().strip()
        if key in DSLD_FALLBACK:
            _unmapped[norm] += 1
            return set(DSLD_FALLBACK[key])

    _unmapped[norm] += 1
    return {Category.OTHER}


# ---------------------------------------------------------------------------
# Allergen detection from ingredient names.
#
# DSLD's allergen statements are frequently absent - 44% of the protein-powder
# catalogue declares nothing at all, including products whose ingredient list
# literally reads "Milk" and "Lactose". An allergen filter that trusts only the
# declaration therefore fails in the dangerous direction, so we also derive
# allergens from the ingredients themselves.
#
# Two rules, learned from the real names in the data:
#
#   1. Match on word boundaries, never bare substrings. "lact" would catch
#      Lactobacillus, Bifidobacterium lactis and Lactase - probiotics and an
#      enzyme, not a milk declaration. Only lactose / lactalbumin /
#      lactoglobulin are actual dairy markers.
#   2. Some names carry an allergen word while belonging to a different
#      allergen entirely. "Coconut Milk" is not dairy (coconut is a tree nut
#      under FDA labelling); "Milk Thistle" is a botanical. The bare `milk`
#      rule is suppressed when such a qualifier is present, while the
#      unambiguous dairy markers below still fire on their own.
#
# Where a term is genuinely ambiguous we flag rather than stay silent: an
# over-inclusive allergen filter costs a user options, an under-inclusive one
# costs them a reaction.
# ---------------------------------------------------------------------------

#: allergen -> regex alternatives that unambiguously indicate it.
#:
#: Audited against every distinct ingredient/nutrient name across the full
#: ~118,000-product DSLD corpus (build_dataset_supplements.py), not just the
#: protein-powder subset - a vocabulary two orders of magnitude larger, where
#: short prefixes stop being safe. "milkfat" and "eggshell"/"eggwhite" are
#: listed explicitly because the general fix below (require a trailing word
#: boundary) would otherwise silently stop matching them, being fused
#: compounds rather than "milk butter" / "egg shell" as separate words.
_ALLERGEN_PATTERNS: dict[str, tuple[str, ...]] = {
    "milk": (
        r"whey",
        r"casein",
        r"caseinate",
        r"lactose",
        r"lactalbumin",
        r"lactoglobulin",
        r"milkfat",
        r"dairy",
    ),
    "soy": (r"soy", r"soya", r"soybean", r"soymilk", r"soynatto"),
    "egg": (r"egg", r"eggshell", r"eggwhite", r"albumen", r"ovalbumin"),
    "wheat": (r"wheat", r"wheatgrass"),
    "gluten": (r"gluten", r"barley", r"barleygrass", r"rye"),
    "peanut": (r"peanut", r"arachis"),
    "tree nut": (
        r"almond",
        r"cashew",
        r"walnut",
        r"pecan",
        r"hazelnut",
        r"pistachio",
        r"macadamia",
        r"brazil nut",
        r"coconut",
    ),
    "fish": (r"fish", r"anchovy", r"salmon", r"cod", r"tilapia"),
    "shellfish": (r"shellfish", r"crustacean", r"shrimp", r"crab", r"lobster", r"krill"),
    "sesame": (r"sesame", r"tahini"),
}

#: `milk` also fires on the bare word, but only when no non-dairy qualifier is
#: present - "Coconut Milk", "Almond Milk", "Oat Milk", "Milk Thistle", or
#: "Milky Oat" (a real, common herbal ingredient - Avena sativa harvested in
#: its milky stage - unrelated to dairy).
_NON_DAIRY_MILK = re.compile(
    r"\b(coconut|almond|oat|oats|soy|soya|rice|hemp|cashew|pea|flax|thistle)\b", re.IGNORECASE
)

#: "Crab Apple" is a fruit. The only false positive this specific, across the
#: full corpus, that survives a whole-word match on its own trigger word.
_NOT_SHELLFISH = re.compile(r"\bcrab\s*apple", re.IGNORECASE)


def detect_allergens(name: str) -> set[str]:
    """
    Allergens implied by a single ingredient name.

    Conservative by design - see the module note above. Returns an empty set
    for names with no allergen signal, which is *not* the same as a claim that
    the ingredient is allergen-free.

    Matching requires a full word, plural "s" tolerated ("Peanuts",
    "Almonds") - not a bare prefix. A prefix-only check (fixed in this
    module after auditing the full ~118k-product corpus) read "Codonopsis" as
    containing "cod" (fish), "Eggplant" as containing "egg", "Crab Apple" as
    containing "crab" (shellfish), and "Glutenase" - an enzyme sold to help
    people *digest* gluten - as containing gluten itself. All four are
    unrelated to the allergen they matched; a filter that invents allergens
    which aren't there is exactly as unsafe as one that misses real ones,
    since it teaches a user to stop trusting the flag at all. The trade-off,
    accepted deliberately: a handful of fused marketing names not on the
    explicit list above (e.g. "SoyLife", "Wheybolic") won't self-identify by
    name alone. Real declared allergens (Trust's `allergens` field) never
    depend on this function.
    """
    found: set[str] = set()
    if not name:
        return found

    for allergen, patterns in _ALLERGEN_PATTERNS.items():
        for pattern in patterns:
            if re.search(rf"\b{pattern}s?\b", name, re.IGNORECASE):
                found.add(allergen)
                break

    # Bare "milk", only when it isn't one of the plant milks.
    if re.search(r"\bmilks?\b", name, re.IGNORECASE) and not _NON_DAIRY_MILK.search(name):
        found.add("milk")

    if "shellfish" in found and _NOT_SHELLFISH.search(name):
        found.discard("shellfish")

    # Wheat implies gluten; the reverse does not hold.
    if "wheat" in found:
        found.add("gluten")

    return found


def looks_proprietary(name: str, description: str | None = None) -> bool:
    """
    Proprietary blends hide per-ingredient doses, which is the mechanism behind
    amino spiking. Worth its own filter.

    "Blend" alone is a weak signal - "Protein Blend" is often an honest
    disclosure of two named sources - so require an explicit proprietary or
    matrix marker.
    """
    text = f"{name} {description or ''}"
    if re.search(r"\bproprietary\b", text, re.IGNORECASE):
        return True
    return bool(re.search(r"\b(matrix|complex)\b", text, re.IGNORECASE))


def unmapped(limit: int = 50) -> list[tuple[str, int]]:
    """Most frequent unmatched ingredient names. This is the to-do list."""
    return _unmapped.most_common(limit)


def reset_unmapped() -> None:
    _unmapped.clear()


def coverage() -> dict[str, int]:
    return {
        "unii_entries": len(UNII_MAP),
        "name_patterns": len(NAME_PATTERNS),
        "unmapped_seen": len(_unmapped),
    }
