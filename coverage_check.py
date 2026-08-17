"""
Taxonomy coverage check against real ingredient rows pulled from 22 live
DSLD labels (4 whey, 6 plant, 4 pea, 4 casein, 4 collagen protein products),
fetched from the public API on 2026-08-17. (name, unii, dsld_category) tuples
transcribed directly from the API responses.
"""
from labellens.taxonomy import categorise, unmapped, coverage
from labellens.schema import Category

ROWS = [
    ("natural Vanilla flavor", None, "botanical"),
    ("Xanthan Gum", "TTV12P4NEE", "complex carbohydrate"),
    ("Sucralose", None, "non-nutrient/non-botanical"),
    ("Salt", None, "non-nutrient/non-botanical"),
    ("hydrolyzed Whey Protein", None, "protein"),
    ("Sunflower Lecithin", None, "fat"),
    ("natural Cocoa powder", None, "botanical"),
    ("Natural & Artificial flavor", None, "other"),
    ("WPI", None, "protein"),
    ("Pea Protein", "7Q50F46595", "protein"),
    ("Brown Rice Protein", None, "protein"),
    ("Cocoa", "D9108TZ9KG", "botanical"),
    ("Cane Sugar", "C151H8M554", "sugar"),
    ("Natural Flavors", None, "other"),
    ("Salt", "451W47IQ8X", "mineral"),
    ("Stevia", None, "botanical"),
    ("Monk Fruit Extract", "NOU2FB51TW", "botanical"),
    ("Soy Protein isolate", None, "protein"),
    ("Wheat Protein", None, "protein"),
    ("Lecithin", None, "fat"),
    ("Silicon Dioxide", "ETJ7Z6XBU4", "mineral"),
    ("Hemp Protein", None, "protein"),
    ("natural Chocolate flavor", None, "botanical"),
    ("Sea Salt", "87GE52P74G", "mineral"),
    ("Vegan Protein Blend", None, "blend"),
    ("Pea Protein isolate", None, "protein"),
    ("Taurine", None, "non-nutrient/non-botanical"),
    ("Rice Protein concentrate", None, "protein"),
    ("Glycine", "TE7660XO1C", "amino acid"),
    ("L-Glutamine", None, "amino acid"),
    ("Complete Protein Blend", None, "blend"),
    ("Brown Rice Protein concentrate", None, "protein"),
    ("Hemp seed Protein", None, "protein"),
    ("Cane Sugar, Evaporated", None, "sugar"),
    ("Cucumber powder", None, "botanical"),
    ("Gum Arabic", None, "botanical"),
    ("Chia", None, "botanical"),
    ("Tricalcium Phosphate", "K4C08XP666", "mineral"),
    ("Spinach powder", None, "botanical"),
    ("Guar Gum", None, "fiber"),
    ("Medium Chain Triglycerides", None, "fat"),
    ("Carrageenan", "5C69YCD2YJ", "complex carbohydrate"),
    ("Dextrin", "2NX48Z0A9G", "sugar"),
    ("Stevia leaf extract", None, "botanical"),
    ("Monk Fruit extract", None, "botanical"),
    ("Ferrous Fumarate", None, "mineral"),
    ("Zinc Oxide", "SOI2LOH54Z", "mineral"),
    ("Vitamin D2", "VS041H42XC", "vitamin"),
    ("Vitamin B12", "8406EY2OQA", "vitamin"),
    ("Fructose", "6YSS42VSEV", "sugar"),
    ("Maltodextrin", "7CVR7L4A2D", "complex carbohydrate"),
    ("BeFlora Soluble Fiber", None, "blend"),
    ("Cellulose", None, "fiber"),
    ("Vegetable Stearate", None, "other"),
    ("Silica", None, "mineral"),
    ("Stearic Acid", "4ELV7Z65AP", "fatty acid"),
    ("Arbonne Protein Matrix Blend", None, "blend"),
    ("Cranberry Protein", None, "protein"),
    ("Rice Protein", None, "protein"),
    ("Chicory", None, "botanical"),
    ("Sunflower Oil", None, "fat"),
    ("Flax Seed", None, "botanical"),
    ("Cinnamon", None, "botanical"),
    ("Tapioca Starch", "24SC3U704I", "complex carbohydrate"),
    ("Dicalcium Phosphate", None, "mineral"),
    ("Rice", None, "botanical"),
    ("Water", None, "other"),
    ("Sodium Ascorbate", None, "vitamin"),
    ("Tocopherol", None, "vitamin"),
    ("Protein Blend", None, "blend"),
    ("Calcium Caseinate", None, "protein"),
    ("Micellar Casein", None, "protein"),
    ("Polydextrose", None, "fiber"),
    ("Cocoa", None, "botanical"),
    ("Natural and Artificial flavors", None, "other"),
    ("Sunflower Oil powder", None, "fat"),
    ("Dipotassium Phosphate", None, "mineral"),
    ("modified Food Starch", None, "other"),
    ("Tocopherols", None, "vitamin"),
    ("Gum Blend", None, "blend"),
    ("Cellulose Gum", None, "fiber"),
    ("Potassium Chloride", None, "non-nutrient/non-botanical"),
    ("Acesulfame Potassium", None, "non-nutrient/non-botanical"),
    ("Sodium Carboxymethyl Cellulose", None, "other"),
    ("Calcium Phosphate", "97Z1WI3NDX", "mineral"),
    ("Creamer", None, "other"),
    ("Diglycerides", None, "non-nutrient/non-botanical"),
    ("Monoglycerides", None, "non-nutrient/non-botanical"),
    ("Sodium Caseinate", None, "protein"),
    ("Salt Substitute", None, "blend"),
    ("Sodium Gluconate", None, "other"),
    ("Caramel color", None, "other"),
    ("Verisol Bioactive Collagen Peptides", None, "protein"),
    ("L-Proline", "9DLQ4CIU6V", "amino acid"),
    ("L-Glycine", "TE7660XO1C", "amino acid"),
    ("L-Lysine", "K3Z4F929H6", "amino acid"),
    ("Hyaluronic Acid", None, "non-nutrient/non-botanical"),
    ("Grape Seed Extract", None, "botanical"),
    ("natural Raspberry flavor", None, "botanical"),
    ("Citric Acid", None, "non-nutrient/non-botanical"),
    ("Collagen 1 & 3", None, "protein"),
    ("Whey", None, "protein"),
    ("Alpha Lactalbumin", None, "protein"),
    ("Beta Lactoglobulin", None, "protein"),
    ("Immunoglobulins", None, "non-nutrient/non-botanical"),
    ("Oat Bran", None, "fiber"),
    ("FOS", None, "fiber"),
    ("Pomegranate Extact", None, "botanical"),
    ("Vanilla Flavorings", None, "other"),
    ("non-fat dry Milk", None, "animal part or source"),
    ("Bovine Collagen Peptides", None, "protein"),
    ("Bovine Bone Broth hydrolyzed Protein", None, "animal part or source"),
    ("Beef Broth powdered", None, "animal part or source"),
    ("Turkey Broth powdered", None, "animal part or source"),
    ("Chicken Broth powdered", None, "animal part or source"),
    ("Peptan Bovine Collagen Peptides", None, "protein"),
    ("Hydrolyzed Beef Protein", None, "protein"),
    ("Chocolate bean powder", None, "botanical"),
    ("Bone Broth Matrix Blend", None, "blend"),
]

if __name__ == "__main__":
    other_hits = []
    for name, unii, cat in ROWS:
        result = categorise(name, unii, cat)
        if result == {Category.OTHER}:
            other_hits.append((name, unii, cat))

    print(f"Total rows checked: {len(ROWS)}")
    print(f"Distinct names: {len({r[0].lower() for r in ROWS})}")
    print(f"Landed in Category.OTHER (uncategorised): {len(other_hits)}")
    print()
    print("-- fell through to OTHER --")
    for name, unii, cat in other_hits:
        print(f"  {name!r:45} unii={unii!r:14} dsld_category={cat!r}")

    print()
    print("-- coverage() --")
    print(coverage())
    print()
    print("-- unmapped() (also includes DSLD-fallback catches, not just pure OTHER) --")
    for name, count in unmapped(50):
        print(f"  {count:>3}x  {name}")
