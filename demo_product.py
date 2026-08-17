"""
What one parsed DSLD label actually contains.

Answers the practical question: does this dataset give brand, product name,
ingredient list, and macros/nutrients in one record? Run it and read the output.

    python demo_product.py
"""

from __future__ import annotations

import json
from pathlib import Path

from labellens.dsld import parse_label

FIXTURE = Path("tests/fixtures/dsld_51157.json")


def show(p) -> None:
    print("=" * 74)
    print(f"  BRAND       {p.brand}")
    print(f"  PRODUCT     {p.name}")
    print(f"  UPC         {p.upc}")
    print(f"  DSLD ID     {p.dsld_id}      on market: {not p.off_market}")
    print(f"  LABEL DATED {p.entry_date}")
    print(f"  MANUFACTURER {p.manufacturer}")
    print(f"  SERVING     {p.serving.quantity}{p.serving.unit} ({p.serving.note})"
          f"  x{p.serving.per_container} per tub")
    print(f"  SOURCE      {p.source_url}")

    m = p.macros
    print("\n  MACROS / NUTRIENTS (per serving, as declared)")
    for label, val, unit in [
        ("Calories", m.calories, ""),
        ("Protein", m.protein_g, "g"),
        ("Total fat", m.total_fat_g, "g"),
        ("Saturated fat", m.saturated_fat_g, "g"),
        ("Total carbs", m.total_carbs_g, "g"),
        ("Sugar", m.sugar_g, "g"),
        ("Added sugar", m.added_sugar_g, "g"),
        ("Fibre", m.fibre_g, "g"),
        ("Cholesterol", m.cholesterol_mg, "mg"),
        ("Sodium", m.sodium_mg, "mg"),
        ("Calcium", m.calcium_mg, "mg"),
        ("Potassium", m.potassium_mg, "mg"),
    ]:
        if val is not None:
            print(f"    {label:<16} {val:>8}{unit}")

    pct = p.protein_pct_by_weight
    print(f"\n    protein by weight   {pct}%")
    print(f"    protein per calorie {m.protein_per_calorie}")

    print(f"\n  INGREDIENTS ({len(p.ingredients)})")
    for i in p.ingredients:
        cats = ", ".join(sorted(c.value for c in i.categories))
        qty = f"{i.quantity}{i.unit}" if i.quantity else ""
        indent = "  " * i.depth
        print(f"    {indent}{i.name:<34} {qty:>12}  [{cats}]")
        if i.unii:
            print(f"    {indent}{'':<34} {'':>12}   unii={i.unii}")

    print(f"\n  OTHER INGREDIENTS ({len(p.other_ingredients)})")
    for i in p.other_ingredients or []:
        cats = ", ".join(sorted(c.value for c in i.categories))
        print(f"    {i.name:<36} [{cats}]")
    if not p.other_ingredients:
        print("    (none declared)")

    print(f"\n  ALLERGENS   {', '.join(p.allergens) or '(none declared)'}")
    print(f"  TARGET      {', '.join(p.target_groups)}")

    t = p.trust
    print("\n  TRUST")
    print(f"    independent certifications  {len(t.certifications)}")
    print(f"    batch-tested, banned subs   {t.batch_tested_for_banned_substances}")
    print(f"    FDA registration claimed    {t.fda_registration_claimed}")
    print(f"    GMP claimed                 {t.gmp_claimed}")
    print(f"    DSHEA disclaimer present    {t.dshea_disclaimer_present}")
    print(f"    >> implies approval,        {t.implies_approval_without_verification}")
    print(f"       unverified")
    print("=" * 74)


if __name__ == "__main__":
    show(parse_label(json.loads(FIXTURE.read_text())))
