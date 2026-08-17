"""
DSLD API client and parser.

Source: NIH Office of Dietary Supplements, Dietary Supplement Label Database.
  API   https://api.ods.od.nih.gov/dsld/v9/
  Docs  https://dsld.od.nih.gov/api-guide
  Data  CC0 1.0 Universal - public domain, attribution requested

Rate limits (per the API guide): 1,000 requests/hour per IP without a key,
10,000 with a free data.gov key. We self-throttle and cache to disk, because
re-fetching 200k labels during development is how you get blocked for an hour.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

from .schema import Certification, Certifier, Ingredient, Macros, Product, Serving, Trust
from .taxonomy import categorise, looks_proprietary

BASE = "https://api.ods.od.nih.gov/dsld/v9"
USER_AGENT = "label-lens/0.1 (research; DSLD via public API)"

CITATION = (
    "National Institutes of Health, Office of Dietary Supplements. "
    "Dietary Supplement Label Database. https://dsld.od.nih.gov/"
)


class DSLDError(RuntimeError):
    pass


class DSLDClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        cache_dir: Path | None = Path(".cache/dsld"),
        min_interval: float = 0.4,  # ~150/hr headroom under the 1,000 limit
    ) -> None:
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.min_interval = min_interval
        self._last_call = 0.0
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- transport ---------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode(params or {})
        url = f"{BASE}/{path.lstrip('/')}" + (f"?{query}" if query else "")

        cache_file = None
        if self.cache_dir:
            safe = urllib.parse.quote(f"{path}?{query}", safe="")[:180]
            cache_file = self.cache_dir / f"{safe}.json"
            if cache_file.exists():
                return json.loads(cache_file.read_text())

        elapsed = time.time() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        if self.api_key:
            req.add_header("X-Api-Key", self.api_key)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            raise DSLDError(f"GET {url} failed: {exc}") from exc
        finally:
            self._last_call = time.time()

        if cache_file:
            cache_file.write_text(json.dumps(payload))
        return payload

    # -- endpoints ---------------------------------------------------------

    def browse_products(self, keyword: str, size: int = 50, page: int = 1) -> dict:
        return self._get(
            "browse-products",
            {"method": "by_keyword", "q": keyword, "size": size, "from": (page - 1) * size},
        )

    def label(self, dsld_id: int) -> dict:
        return self._get(f"label/{dsld_id}")

    def search_filter(self, query: str, size: int = 50, page: int = 1) -> dict:
        return self._get(
            "search-filter",
            {"q": query, "size": size, "from": (page - 1) * size},
        )

    # -- iteration ---------------------------------------------------------

    def iter_ids(self, keyword: str, *, limit: int | None = None) -> Iterator[int]:
        """
        Yield DSLD ids for a keyword, paging until exhausted or `limit` reached.
        """
        seen: set[int] = set()
        page = 1
        while True:
            payload = self.browse_products(keyword, size=50, page=page)
            hits = payload.get("hits", [])
            if not hits:
                return
            for hit in hits:
                try:
                    dsld_id = int(hit["_id"])
                except (KeyError, TypeError, ValueError):
                    continue
                if dsld_id in seen:
                    continue
                seen.add(dsld_id)
                yield dsld_id
                if limit and len(seen) >= limit:
                    return
            page += 1


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

#: DSLD's `ingredientRows` conflates two different things: Nutrition Facts
#: panel rows (Calories, Total Fat, Sodium...) and actual ingredients
#: (whey protein, sucralose, xanthan gum). We split them: panel rows populate
#: `macros`, everything else becomes an `Ingredient`.
#:
#: Matched on normalised DSLD `name`.
_MACRO_FIELDS: dict[str, str] = {
    "calories": "calories",
    "protein": "protein_g",
    "total fat": "total_fat_g",
    "saturated fat": "saturated_fat_g",
    "cholesterol": "cholesterol_mg",
    "total carbohydrates": "total_carbs_g",
    "total carbohydrate": "total_carbs_g",
    "sugar": "sugar_g",
    "sugars": "sugar_g",
    "added sugars": "added_sugar_g",
    "dietary fiber": "fibre_g",
    "dietary fibre": "fibre_g",
    "sodium": "sodium_mg",
    "calcium": "calcium_mg",
    "potassium": "potassium_mg",
}

#: Panel rows with no macro field of their own that still must not appear in
#: the ingredient list. "Calories from Fat" is a derived panel line, not a
#: thing in the tub.
_PANEL_ONLY: frozenset[str] = frozenset(
    set(_MACRO_FIELDS) | {"calories from fat", "trans fat", "total sugars"}
)

#: Units we normalise to. DSLD is inconsistent: "Gram(s)", "g", "mg", "mcg".
_UNIT_TO_G = {"gram(s)": 1.0, "g": 1.0, "mg": 0.001, "mcg": 0.000001}
_UNIT_TO_MG = {"gram(s)": 1000.0, "g": 1000.0, "mg": 1.0, "mcg": 0.001}


def _first_quantity(row: dict) -> tuple[float | None, str | None, float | None]:
    q = (row.get("quantity") or [{}])[0]
    return q.get("quantity"), q.get("unit"), _percent_dv(q)


def _percent_dv(q: dict) -> float | None:
    for group in q.get("dailyValueTargetGroup") or []:
        if group.get("percent") is not None:
            return group["percent"]
    return None


def _walk(rows: list[dict], depth: int = 0) -> Iterator[tuple[dict, int]]:
    for row in rows or []:
        yield row, depth
        yield from _walk(row.get("nestedRows") or [], depth + 1)


def _set_macro(macros: Macros, field: str, value: float | None, unit: str | None) -> None:
    if value is None:
        return
    u = (unit or "").lower()
    if field.endswith("_g"):
        factor = _UNIT_TO_G.get(u)
        value = value * factor if factor else value
    elif field.endswith("_mg"):
        factor = _UNIT_TO_MG.get(u)
        value = value * factor if factor else value
    setattr(macros, field, round(value, 4))


def parse_label(raw: dict) -> Product:
    """Turn a DSLD label payload into a Product."""
    serving_raw = (raw.get("servingSizes") or [{}])[0]
    source_url = f"https://dsld.od.nih.gov/label/{raw['id']}"

    product = Product(
        dsld_id=int(raw["id"]),
        brand=raw.get("brandName") or "",
        name=raw.get("fullName") or "",
        upc=raw.get("upcSku") or None,
        off_market=bool(raw.get("offMarket")),
        entry_date=raw.get("entryDate"),
        physical_state=(raw.get("physicalState") or {}).get("langualCodeDescription"),
        product_type=(raw.get("productType") or {}).get("langualCodeDescription"),
        serving=Serving(
            quantity=serving_raw.get("minQuantity"),
            unit=serving_raw.get("unit"),
            note=serving_raw.get("notes"),
            per_container=raw.get("servingsPerContainer"),
        ),
        target_groups=list(raw.get("targetGroups") or []),
        source_url=source_url,
    )

    # -- ingredients and macros -------------------------------------------
    for row, depth in _walk(raw.get("ingredientRows") or []):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        qty, unit, pct = _first_quantity(row)
        norm = name.lower().strip()

        if norm in _MACRO_FIELDS:
            _set_macro(product.macros, _MACRO_FIELDS[norm], qty, unit)

        # Panel rows populate `macros` and are excluded from the ingredient
        # list, so that list reflects what is actually in the tub. Applied
        # uniformly — an earlier version skipped only some panel rows, which
        # left Sodium and Calcium sitting in the ingredient list next to
        # sucralose. Inconsistent, and misleading to a reader.
        if norm in _PANEL_ONLY:
            continue

        unii = row.get("uniiCode")
        if unii in ("0", "1", ""):  # DSLD placeholders, not real UNIIs
            unii = None

        product.ingredients.append(
            Ingredient(
                name=name,
                unii=unii,
                dsld_category=row.get("category"),
                categories=categorise(name, unii, row.get("category")),
                quantity=qty,
                unit=unit,
                percent_dv=pct,
                depth=depth,
                is_proprietary_blend=looks_proprietary(name, row.get("notes")),
            )
        )

    # -- other ingredients -------------------------------------------------
    for row in (raw.get("otheringredients") or {}).get("ingredients") or []:
        name = (row.get("name") or "").strip()
        # DSLD uses a "Header" ingredientGroup for label furniture such as
        # "Absolutely None". Not an ingredient.
        if not name or (row.get("ingredientGroup") or "").lower() == "header":
            continue
        unii = row.get("uniiCode")
        if unii in ("0", "1", ""):
            unii = None
        product.other_ingredients.append(
            Ingredient(
                name=name,
                unii=unii,
                dsld_category=row.get("category"),
                categories=categorise(name, unii, row.get("category")),
                is_proprietary_blend=looks_proprietary(name),
            )
        )

    # -- statements: allergens and trust claims ---------------------------
    product.trust = _parse_trust(raw.get("statements") or [], source_url)
    product.allergens = _parse_allergens(raw.get("statements") or [])

    contacts = raw.get("contacts") or []
    if contacts:
        details = contacts[0].get("contactDetails") or {}
        product.manufacturer = details.get("name")
        product.manufacturer_country = details.get("country") or None

    return product


#: Certifier seal text -> Certifier. Matched against lowercased statement
#: text (mainly "Seals/Symbols" rows, but the same wording often repeats in
#: "General Statements"). These are trademarked program names printed
#: verbatim on the label, not a fuzzy join against an external certifier
#: list - see README for that separate, lower-confidence join.
_CERTIFIER_PHRASES: list[tuple[str, Certifier]] = [
    ("certified for sport", Certifier.NSF_CERTIFIED_FOR_SPORT),
    ("nsf contents certified", Certifier.NSF_CONTENTS_CERTIFIED),
    ("informed-sport", Certifier.INFORMED_SPORT),
    ("informed sport", Certifier.INFORMED_SPORT),
    ("informed-choice", Certifier.INFORMED_CHOICE),
    ("informed choice", Certifier.INFORMED_CHOICE),
    ("usp verified", Certifier.USP_VERIFIED),
    ("bscg certified drug free", Certifier.BSCG),
    ("banned substances control group", Certifier.BSCG),
]


def _parse_trust(statements: list[dict], source_url: str) -> Trust:
    """
    Extract trust signals from label statement text.

    Two different things live here and must not be conflated: self-asserted
    CLAIMS (fda_registration_claimed, gmp_claimed, ...) versus real
    certifications detected from a trademarked seal name actually printed on
    the label (e.g. "NSF Certified for Sport", "Informed-Choice.org"). Only
    the latter populates `certifications` / `has_independent_verification`.
    """
    trust = Trust()
    seen: set[Certifier] = set()
    for st in statements:
        text = (st.get("notes") or "").lower()
        stype = (st.get("type") or "").lower()

        if "fda disclaimer" in stype or "not been evaluated by the food and drug" in text:
            trust.dshea_disclaimer_present = True
        if "fda registration" in text or "fda registered" in text:
            trust.fda_registration_claimed = True
        if "gmp" in text or "21 cfr part 111" in text:
            trust.gmp_claimed = True
        if "third party tested" in text or "third-party tested" in text:
            trust.third_party_tested_claimed = True

        for phrase, certifier in _CERTIFIER_PHRASES:
            if phrase in text and certifier not in seen:
                seen.add(certifier)
                trust.certifications.append(
                    Certification(certifier=certifier, source_url=source_url)
                )
    return trust


_ALLERGEN_TERMS = (
    "milk", "soy", "egg", "wheat", "peanut", "tree nut", "fish",
    "shellfish", "sesame", "gluten",
)


def _parse_allergens(statements: list[dict]) -> list[str]:
    found: set[str] = set()
    for st in statements:
        stype = (st.get("type") or "").lower()
        text = (st.get("notes") or "").lower()
        if "allerg" not in stype and "allergen" not in text:
            continue
        # "Soy Free" / "Gluten Free" are the opposite of a warning
        for term in _ALLERGEN_TERMS:
            if term in text and f"{term} free" not in text and f"{term}-free" not in text:
                found.add(term)
    return sorted(found)
