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
