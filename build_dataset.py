"""
Builds a real Dataset (brand, product, macros, ingredients, trust) from the
25 DSLD labels actually fetched and read in this session -- 4 whey (NutraBio
x3, Bluebonnet, Extreme Edge, GHOST), 6 plant, 4 pea, 4 casein, 4 collagen.

Fields are transcribed from the live API responses, trimmed to what the app
needs (marketing statement text dropped; macro figures, ingredient names/
UNII/quantities, allergens, and trust-relevant claims kept verbatim).
Categorisation runs through the real taxonomy.categorise(), not hand-assigned.

    python build_dataset.py
"""

from __future__ import annotations

import json
from pathlib import Path

from labellens.schema import (
    Certification,
    Certifier,
    Dataset,
    Ingredient,
    Macros,
    Product,
    Serving,
    Trust,
)
from labellens.taxonomy import categorise, looks_proprietary, unmapped, coverage

# Source URLs for the certification claims found in each label's own
# `statements` text (not a separate NSF/Informed Sport database join).
_CERT_SOURCE = {
    "nsf_certified_for_sport": "https://dsld.od.nih.gov/label/205264",
    "informed_choice": "https://dsld.od.nih.gov/label/67269",
}

# Each entry: compact fields transcribed from the raw DSLD label JSON.
RAW = [
    # -- whey --------------------------------------------------------------
    dict(id=51157, brand="NutraBio", name="100% Hydrolyzed Whey Protein Alpine Vanilla",
         upc="6 49908 25541 1", off_market=False, entry="2015-10-22",
         mfr="NutraBio Labs, Inc.", serving=(32.5, "Gram(s)", "1 scoop", "70"),
         macros=dict(cal=120, protein=25, fat=1.5, satfat=1, carbs=2, sugar=2,
                     chol=15, sodium=60, calcium=15, potassium=20),
         ingredients=[
             ("natural Vanilla flavor", None, 610, "mg"),
             ("Xanthan Gum", "TTV12P4NEE", 100, "mg"),
             ("Sucralose", None, 68, "mg"),
             ("Salt", None, 65, "mg"),
             ("hydrolyzed Whey Protein", None, 31.6, "Gram(s)"),
         ],
         allergens=["milk"], fda_reg=True, gmp=True, dshea=True, tpt=False, certs=[]),
    dict(id=51156, brand="NutraBio", name="100% Hydrolyzed Whey Protein Alpine Vanilla",
         upc="6 49908 25540 4", off_market=False, entry="2016-11-21",
         mfr="NutraBio Labs, Inc.", serving=(34.7, "Gram(s)", "1 scoop", "65"),
         macros=dict(cal=140, protein=25, fat=2, satfat=1.5, fiber=1, carbs=4, sugar=2,
                     chol=10, sodium=80, calcium=20, potassium=60),
         ingredients=[
             ("natural Cocoa powder", None, 2380, "mg"),
             ("Natural & Artificial flavor", None, 470, "mg"),
             ("Salt", None, 110, "mg"),
             ("Xanthan Gum", "TTV12P4NEE", 100, "mg"),
             ("Sucralose", None, 70, "mg"),
             ("hydrolyzed Whey Protein", None, 31.6, "Gram(s)"),
         ],
         allergens=["milk"], fda_reg=True, gmp=True, dshea=True, tpt=False, certs=[]),
    dict(id=51366, brand="NutraBio", name="100% Hydrolyzed Whey Protein Unflavored",
         upc="6 49908 51340 5", off_market=True, entry="2015-10-22",
         mfr="NutraBio Labs, Inc.", serving=(31.2, "Gram(s)", "1 scoop", "29"),
         macros=dict(cal=120, protein=25, fat=1.5, satfat=1, carbs=2, sugar=2,
                     chol=15, sodium=30, calcium=16, potassium=20),
         ingredients=[("hydrolyzed Whey Protein", None, 31.2, "Gram(s)")],
         allergens=["milk"], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=179477, brand="Bluebonnet", name="100% Natural Whey Protein Isolate Natural Chocolate",
         upc="7 43715 01568 5", off_market=False, entry="2018-07-25",
         mfr="Bluebonnet Nutrition Corporation", serving=(33, "Gram(s)", "1 scoop", "14"),
         macros=dict(cal=125, protein=26, fat=0.5, satfat=0.5, carbs=3, sugar=1.5,
                     added_sugar=0, fiber=0.5, chol=15, sodium=120, calcium=130,
                     potassium=225),
         ingredients=[
             ("undenatured Whey Protein isolate", None, None, None),
             ("Dutch Cocoa", None, None, None),
             ("natural Chocolate flavor", None, None, None),
             ("non-GMO Sunflower Lecithin", None, None, None),
             ("Stevia extract", None, None, None),
         ],
         allergens=["milk"], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=205264, brand="Extreme Edge", name="100% Pure Whey Protein Isolate Chocolate Flavor",
         upc="7 43715 01827 3", off_market=False, entry="2019-09-24",
         mfr="Bluebonnet Nutrition Corp.", serving=(33, "Gram(s)", "1 scoop", "28"),
         macros=dict(cal=125, protein=26, fat=0.5, satfat=0.5, carbs=3, sugar=1.5,
                     added_sugar=0, fiber=0.5, chol=15, sodium=125, calcium=130,
                     potassium=250),
         ingredients=[
             ("Dutch Cocoa", None, None, None),
             ("natural Chocolate flavor", None, None, None),
             ("non-GMO Sunflower Lecithin", None, None, None),
             ("Stevia extract", None, None, None),
         ],
         allergens=["milk"], fda_reg=False, gmp=False, dshea=True, tpt=False,
         # "NSF / Certified for Sport ... tested for 200+ banned substances" in statements
         certs=["nsf_certified_for_sport"]),
    dict(id=223159, brand="GHOST", name="100% Whey Protein 25 g Coffee Ice Cream",
         upc="8 53513 00800 7", off_market=False, entry="2020-06-24",
         mfr="GHOST", serving=(33, "Gram(s)", "1 Rounded Scoop", "28"),
         macros=dict(cal=120, protein=25, fat=1.5, satfat=1, transfat=0, carbs=3,
                     sugar=1, added_sugar=0, fiber=0, chol=40, sodium=95,
                     vitd=0, calcium=135, iron=0, potassium=112),
         ingredients=[
             ("hydrolyzed Whey Protein isolate", None, None, None),
             ("Whey Protein concentrate", None, None, None),
             ("Whey Protein isolate", None, None, None),
             ("Natural and Artificial flavor", None, None, None),
             ("100% Columbian Coffee", None, None, None),
             ("Salt", None, None, None),
             ("Bromelain", "U182GP2CF3", None, None),
             ("Lactase", "37515NWH9U", None, None),
             ("Proteases", None, None, None),
             ("Cellulose Gum", None, None, None),
             ("Xanthan Gum", "TTV12P4NEE", None, None),
             ("Sucralose", None, None, None),
             ("Acesulfame Potassium", None, None, None),
         ],
         allergens=["milk"], fda_reg=False, gmp=True, dshea=True, tpt=False, certs=[]),
    # -- plant ---------------------------------------------------------------
    dict(id=332667, brand="Momentous", name="100% Plant Protein Chocolate Flavor",
         upc="", off_market=False, entry="2025-07-24",
         mfr="Momentous", serving=(32.7, "Gram(s)", "1 scoop", "22"),
         macros=dict(cal=130, protein=20, fat=2.5, satfat=0.5, fiber=2, sugar=2,
                     added_sugar=2, carbs=6, calcium=140, iron=5, sodium=300,
                     potassium=220),
         ingredients=[
             ("Pea Protein", "7Q50F46595", 24.08, "Gram(s)"),
             ("Brown Rice Protein", None, 1, "Gram(s)"),
             ("Cocoa", "D9108TZ9KG", None, None),
             ("Cane Sugar", "C151H8M554", None, None),
             ("Natural Flavors", None, None, None),
             ("Salt", "451W47IQ8X", None, None),
             ("Stevia", None, None, None),
             ("Monk Fruit Extract", "NOU2FB51TW", None, None),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=False, tpt=False, certs=[]),
    dict(id=208054, brand="Nutrilite", name="All Plant Protein Powder",
         upc="11-0415", off_market=True, entry="2019-11-21",
         mfr="Amway Corp.", serving=(12.5, "Gram(s)", "2 Tbsp", "36"),
         macros=dict(cal=50, fat=0.5, chol=0, sodium=125, protein=10, iron=1),
         ingredients=[
             ("Soy Protein isolate", None, None, None),
             ("Wheat Protein", None, None, None),
             ("Pea Protein", None, None, None),
             ("Lecithin", None, None, None),
             ("Silicon Dioxide", "ETJ7Z6XBU4", None, None),
         ],
         allergens=["soy", "wheat"], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=263731, brand="Woodstock Vitamins",
         name="Balanced Plant Protein Blend Natural Chocolate Flavor",
         upc="", off_market=False, entry="2021-12-18",
         mfr="Village Vitality LLC", serving=(23, "Gram(s)", "1 Scoop", "17"),
         macros=dict(cal=90, fat=2, satfat=0.5, carbs=2, protein=15, calcium=20,
                     sodium=225, potassium=110),
         ingredients=[
             ("Pea Protein", None, None, None),
             ("Hemp Protein", None, None, None),
             ("natural Chocolate flavor", None, None, None),
             ("Stevia", None, None, None),
             ("Sea Salt", "87GE52P74G", None, None),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=263469, brand="Woodstock Vitamins", name="Complete Plant Protein",
         upc="6 69439 80694 4", off_market=False, entry="2022-05-19",
         mfr="Village Vitality LLC", serving=(21, "Gram(s)", "1 scoop", "14"),
         macros=dict(cal=80, fat=1, fiber=1, protein=17, iron=3, sodium=300),
         ingredients=[
             ("Vegan Protein Blend", None, None, None),
             ("Pea Protein isolate", None, None, None),
             ("Taurine", None, None, None),
             ("Rice Protein concentrate", None, None, None),
             ("Glycine", "TE7660XO1C", None, None),
             ("L-Glutamine", None, None, None),
         ],
         allergens=[], fda_reg=False, gmp=True, dshea=False, tpt=False, certs=[],
         proprietary=True),
    dict(id=221608, brand="Body Fortress", name="Complete Plant Protein Chocolate",
         upc="0 74312 80115 0", off_market=False, entry="2020-06-24",
         mfr="United States Nutrition, Inc.", serving=(38.1, "Gram(s)", "1 Rounded Scoop", "18"),
         macros=dict(cal=140, fat=3.5, satfat=1, transfat=0, chol=0, sodium=400,
                     potassium=280, fiber=4, sugar=3, protein=20),
         ingredients=[
             ("Complete Protein Blend", None, None, None),
             ("Brown Rice Protein concentrate", None, None, None),
             ("Hemp seed Protein", None, None, None),
             ("Pea Protein isolate", None, None, None),
             ("Cocoa", None, None, None),
             ("Cane Sugar, Evaporated", None, None, None),
             ("Cucumber powder", None, None, None),
             ("Natural Flavors", None, None, None),
             ("Gum Arabic", None, None, None),
             ("Chia", None, None, None),
             ("Tricalcium Phosphate", "K4C08XP666", None, None),
             ("Spinach powder", None, None, None),
             ("Guar Gum", None, None, None),
             ("Medium Chain Triglycerides", None, None, None),
             ("Sea Salt", None, None, None),
             ("Carrageenan", "5C69YCD2YJ", None, None),
             ("Dextrin", "2NX48Z0A9G", None, None),
             ("Stevia leaf extract", None, None, None),
             ("Monk Fruit extract", None, None, None),
             ("Ferrous Fumarate", None, None, None),
             ("Zinc Oxide", "SOI2LOH54Z", None, None),
             ("Vitamin D2", "VS041H42XC", None, None),
             ("Vitamin B12", "8406EY2OQA", None, None),
         ],
         allergens=[], fda_reg=False, gmp=True, dshea=False, tpt=False, certs=[],
         proprietary=True),
    dict(id=221588, brand="Body Fortress", name="Complete Plant Protein Vanilla",
         upc="0 74312 80116 7", off_market=False, entry="2020-06-24",
         mfr="United States Nutrition, Inc.", serving=(38.2, "Gram(s)", "1 Rounded Scoop", "18"),
         macros=dict(cal=140, fat=3, satfat=1, transfat=0, chol=0, sodium=310,
                     potassium=105, fiber=4, sugar=3, protein=20),
         ingredients=[
             ("Complete Protein Blend", None, None, None),
             ("Brown Rice Protein concentrate", None, None, None),
             ("Hemp seed Protein", None, None, None),
             ("Pea Protein isolate", None, None, None),
             ("Natural Flavors", None, None, None),
             ("Cane Sugar, Evaporated", None, None, None),
             ("Gum Arabic", None, None, None),
             ("Cucumber powder", None, None, None),
             ("Chia", None, None, None),
             ("Tricalcium Phosphate", "K4C08XP666", None, None),
             ("Guar Gum", None, None, None),
             ("Medium Chain Triglycerides", None, None, None),
             ("Carrageenan", "5C69YCD2YJ", None, None),
             ("Dextrin", "2NX48Z0A9G", None, None),
             ("dried Banana powder", None, None, None),
             ("Stevia leaf extract", None, None, None),
             ("Monk Fruit extract", None, None, None),
             ("Ferrous Fumarate", None, None, None),
             ("Zinc Oxide", "SOI2LOH54Z", None, None),
             ("Vitamin D2", "VS041H42XC", None, None),
             ("Vitamin B12", "8406EY2OQA", None, None),
         ],
         allergens=[], fda_reg=False, gmp=True, dshea=False, tpt=False, certs=[],
         proprietary=True),
    # -- pea -------------------------------------------------------------
    dict(id=71606, brand="Hard Rhino", name="100% Pea Protein Isolate Unflavored",
         upc="8 18132 89681 7", off_market=False, entry="2017-03-24",
         mfr="Guardian Wholesale", serving=(20, "Gram(s)", "~4 tbsp", "25"),
         macros=dict(cal=74, fat=0.8, satfat=0.1, chol=0, sodium=300, fiber=0,
                     sugar=0, protein=16, iron=0),
         ingredients=[("Pea Protein isolate", None, None, None)],
         allergens=[], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=217266, brand="Nutritional Concepts", name="100% Pure Pea Protein Unflavored",
         upc="0 95234 97152 3", off_market=False, entry="2020-04-23",
         mfr="Nutritional Concepts", serving=(30, "Gram(s)", "~2 heaping scoops", "30"),
         macros=dict(cal=130, fat=2, satfat=0.5, sodium=300, fiber=1, sugar=0,
                     protein=24),
         ingredients=[("Silicon Dioxide", "ETJ7Z6XBU4", None, None)],
         allergens=[], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=49919, brand="PureFormulas", name="Essential Pea Protein Vanilla Bean Flavor",
         upc="PUF1068", off_market=True, entry="2015-08-25",
         mfr="PureFormulas", serving=(30.2, "Gram(s)", "1 heaping scoop", "30"),
         macros=dict(cal=95, carbs=8, fiber=1, sugar=5, protein=16),
         ingredients=[
             ("Yellow Pea Protein", None, None, None),
             ("Fructose", "6YSS42VSEV", None, None),
             ("natural Vanilla flavor", None, None, None),
             ("Maltodextrin", "7CVR7L4A2D", None, None),
             ("BeFlora Soluble Fiber", None, None, None),
             ("Cellulose", None, None, None),
             ("Vegetable Stearate", None, None, None),
             ("Silica", None, None, None),
             ("Stearic Acid", "4ELV7Z65AP", None, None),
         ],
         allergens=["milk"], fda_reg=False, gmp=False, dshea=False, tpt=False, certs=[],
         proprietary=True),
    dict(id=273876, brand="Arbonne", name="FeelFit Pea Protein Shake Banana Pancake Flavor",
         upc="80004449", off_market=True, entry="2023-01-23",
         mfr="Arbonne International, LLC", serving=(40, "Gram(s)", "2 Scoops", "30"),
         macros=dict(cal=160, fat=3, satfat=0.5, transfat=0, chol=0, carbs=13,
                     fiber=3, sugar=7, added_sugar=7, protein=20, sodium=420,
                     potassium=200, iron=4),
         ingredients=[
             ("Arbonne Protein Matrix Blend", None, None, None),
             ("Cane Sugar", None, None, None),
             ("Gum Arabic", None, None, None),
             ("Natural Flavors", None, None, None),
             ("Chicory", None, None, None),
             ("Sunflower Oil", None, None, None),
             ("Flax Seed", None, None, None),
             ("Stevia leaf extract", None, None, None),
             ("Xanthan Gum", "TTV12P4NEE", None, None),
             ("Cinnamon", None, None, None),
             ("Guar Gum", None, None, None),
             ("Tapioca Starch", "24SC3U704I", None, None),
             ("Dicalcium Phosphate", None, None, None),
             ("Tricalcium Phosphate", "K4C08XP666", None, None),
             ("Rice", None, None, None),
             ("Water", None, None, None),
             ("Sodium Ascorbate", None, None, None),
             ("Tocopherol", None, None, None),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[],
         proprietary=True),
    # -- casein --------------------------------------------------------------
    dict(id=16869, brand="GNC Pro Performance", name="100% Casein Protein Chocolate",
         upc="0 48107 09047 0", off_market=True, entry="2013-12-24",
         mfr="General Nutrition Corporation", serving=(42, "Gram(s)", "1 scoop", "21"),
         macros=dict(cal=160, fat=1.5, satfat=1, transfat=0, chol=10, sodium=260,
                     fiber=5, sugar=1, protein=25, iron=8, calcium=50),
         ingredients=[
             ("Protein Blend", None, None, None),
             ("Polydextrose", None, None, None),
             ("Cocoa", None, None, None),
             ("Natural and Artificial flavors", None, None, None),
             ("Sunflower Oil powder", None, None, None),
             ("Gum Blend", None, None, None),
             ("Lecithin", None, None, None),
             ("Salt", None, None, None),
             ("Potassium Chloride", None, None, None),
             ("Acesulfame Potassium", None, None, None),
             ("Sucralose", None, None, None),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=False, tpt=False, certs=[]),
    dict(id=334148, brand="Body Attack Sports Nutrition", name="100% Casein Protein Chocolate Cream",
         upc="4 250350 517994", off_market=False, entry="2025-07-24",
         mfr="Body Attack Sports Nutrition GmbH & Co. KG", serving=(30, "Gram(s)", "1.5 scoops", "30"),
         macros=dict(cal=111, fat=0.3, satfat=0.3, carbs=1.4, sugar=0.3, protein=25,
                     sodium=400, calcium=787),
         ingredients=[
             ("Calcium Caseinate", None, None, None),
             ("Micellar Casein", None, None, None),
             ("Cocoa, Powder", "D9108TZ9KG", None, None),
             ("Flavoring", None, None, None),
             ("Salt", "451W47IQ8X", None, None),
             ("Xanthan Gum", "TTV12P4NEE", None, None),
             ("Sodium Carboxymethyl Cellulose", None, None, None),
             ("Carrageenan", "5C69YCD2YJ", None, None),
             ("Sucralose", "96K6UQ3ZD4", None, None),
             ("Acesulfame Potassium", None, None, None),
             ("Calcium Phosphate", "97Z1WI3NDX", None, None),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=False, tpt=False, certs=[]),
    dict(id=33547, brand="GNC Pro Performance", name="100% Casein Protein Chocolate Peanut Butter",
         upc="0 48107 09902 2", off_market=True, entry="2014-05-23",
         mfr="General Nutrition Corporation", serving=(42, "Gram(s)", "1 scoop", "21"),
         macros=dict(cal=160, fat=1.5, satfat=0, chol=10, sodium=220, fiber=3,
                     sugar=2, protein=25, calcium=60),
         ingredients=[
             ("Protein Blend", None, None, None),
             ("Polydextrose", None, None, None),
             ("Cocoa", None, None, None),
             ("Natural and Artificial flavors", None, None, None),
             ("Creamer", None, None, None),
             ("Salt Substitute", None, None, None),
             ("Gum Blend", None, None, None),
             ("Lecithin", None, None, None),
             ("Salt", None, None, None),
             ("Sucralose", None, None, None),
             ("Acesulfame Potassium", None, None, None),
             ("Caramel color", None, None, None),
         ],
         allergens=["milk", "soy"], fda_reg=False, gmp=False, dshea=False, tpt=False, certs=[]),
    dict(id=67269, brand="GNC Pro Performance", name="100% Casein Protein Chocolate Supreme",
         upc="0 48107 15761 6", off_market=False, entry="2016-11-21",
         mfr="General Nutrition Corp.", serving=(35, "Gram(s)", "1/2-2 scoops", "28"),
         macros=dict(cal=120, fat=1, satfat=0.5, chol=20, sodium=230, potassium=290,
                     fiber=1, sugar=1, protein=25, calcium=0, iron=0),
         ingredients=[
             ("Micellar Casein", None, None, None),
             ("Cocoa", None, None, None),
             ("Natural and Artificial flavors", None, None, None),
             ("Creamer", None, None, None),
             ("Salt Substitute", None, None, None),
             ("Gum Blend", None, None, None),
             ("Lecithin", None, None, None),
             ("Salt", None, None, None),
             ("Sucralose", None, None, None),
             ("Acesulfame Potassium", None, None, None),
             ("Polydextrose", None, None, None),
             ("Caramel color", None, None, None),
         ],
         allergens=["milk", "soy"], fda_reg=False, gmp=False, dshea=False, tpt=False,
         # "Informed-Choice.org Trusted by sport... tested for over 145 banned
         # substances on the 2015 WADA Prohibited List"
         certs=["informed_choice"]),
    # -- collagen --------------------------------------------------------
    dict(id=248510, brand="IVL", name="24/7 Beauty Collagen Protein Raspberry Flavored",
         upc="X002GXRJ45", off_market=False, entry="2021-07-27",
         mfr="Independent Vital Life, LLC", serving=(6.4, "Gram(s)", "1 Scoop", "30"),
         macros=dict(cal=25, carbs=2, fiber=2, protein=2, sodium=25),
         ingredients=[
             ("Verisol Bioactive Collagen Peptides", None, 2500, "mg"),
             ("L-Proline", "9DLQ4CIU6V", 550, "mg"),
             ("L-Glycine", "TE7660XO1C", 550, "mg"),
             ("L-Lysine", "K3Z4F929H6", 550, "mg"),
             ("Hyaluronic Acid", None, 200, "mg"),
             ("Grape Seed Extract", None, 50, "mg"),
             ("natural Raspberry flavor", None, None, None),
             ("Cellulose Gum", None, None, None),
             ("Xanthan Gum", "TTV12P4NEE", None, None),
             ("Carrageenan", "5C69YCD2YJ", None, None),
             ("Citric Acid", None, None, None),
             ("Stevia leaf extract", None, None, None),
             ("Natural Flavors", None, None, None),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=18998, brand="youtheory", name="Anti-Aging Collagen Protein Shake Vanilla",
         upc="8 53244 00308 1", off_market=True, entry="2013-04-25",
         mfr="Nutrawise", serving=(33, "Gram(s)", "1 scoop", "21"),
         macros=dict(cal=110, fat=0.8, sodium=42, potassium=60, carbs=3.4,
                     fiber=0.6, sugar=2.8, protein=20, calcium=1000, iron=18),
         ingredients=[
             ("Collagen 1 & 3", None, 10, "g"),
             ("Whey", None, 10, "g"),
             ("Alpha Lactalbumin", None, None, None),
             ("Beta Lactoglobulin", None, None, None),
             ("Immunoglobulins", None, None, None),
             ("Oat Bran", None, None, None),
             ("Guar Gum", None, None, None),
             ("FOS", None, None, None),
             ("Pomegranate Extact", None, None, None),
             ("Vanilla Flavorings", None, None, None),
             ("Fructose", "6YSS42VSEV", None, None),
             ("non-fat dry Milk", None, None, None),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=261645, brand="Peak Performance", name="Bone Broth + Collagen Protein",
         upc="X001HDCLXJ", off_market=True, entry="2022-02-23",
         mfr="Peak Performance Life LLC", serving=(16, "Gram(s)", "1 Scoop", "30"),
         macros=dict(cal=60, protein=14, sodium=100),
         ingredients=[
             ("Bovine Collagen Peptides", None, 8, "Gram(s)"),
             ("Bovine Bone Broth hydrolyzed Protein", None, 8, "Gram(s)"),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[]),
    dict(id=247876, brand="Terra Origin", name="Collagen + Protein Bone Broth Chocolate",
         upc="8 57668 00711 3", off_market=True, entry="2021-07-27",
         mfr="Terra Origin Inc", serving=(25.9, "Gram(s)", "Approx. 1 Scoop", "20"),
         macros=dict(cal=100, fat=1.5, satfat=1, chol=5, carbs=3, fiber=1,
                     protein=17, sodium=150, potassium=169),
         ingredients=[
             ("Bone Broth Matrix Blend", None, 6.59, "Gram(s)"),
             ("Beef Broth powdered", None, None, None),
             ("Turkey Broth powdered", None, None, None),
             ("Chicken Broth powdered", None, None, None),
             ("Medium Chain Triglycerides", None, 1.25, "Gram(s)"),
             ("Stevia leaf extract", None, 200, "mg"),
             ("Peptan Bovine Collagen Peptides", None, None, None),
             ("Hydrolyzed Beef Protein", None, None, None),
             ("Chocolate bean powder", None, None, None),
             ("Maltodextrin", "7CVR7L4A2D", None, None),
             ("Natural Flavors", None, None, None),
             ("Silicon Dioxide", "ETJ7Z6XBU4", None, None),
         ],
         allergens=[], fda_reg=False, gmp=False, dshea=True, tpt=False, certs=[],
         proprietary=True),
]


def build() -> Dataset:
    ds = Dataset(
        generated="2026-08-17T00:00:00Z",
        query="whey/plant/pea/casein/collagen protein (curated sample)",
    )
    for r in RAW:
        p = Product(
            dsld_id=r["id"], brand=r["brand"], name=r["name"], upc=r["upc"] or None,
            off_market=r["off_market"], entry_date=r["entry"], manufacturer=r["mfr"],
            serving=Serving(quantity=r["serving"][0], unit=r["serving"][1],
                             note=r["serving"][2], per_container=r["serving"][3]),
            macros=Macros(
                calories=r["macros"].get("cal"), protein_g=r["macros"].get("protein"),
                total_fat_g=r["macros"].get("fat"), saturated_fat_g=r["macros"].get("satfat"),
                cholesterol_mg=r["macros"].get("chol"), total_carbs_g=r["macros"].get("carbs"),
                sugar_g=r["macros"].get("sugar"), added_sugar_g=r["macros"].get("added_sugar"),
                fibre_g=r["macros"].get("fiber"), sodium_mg=r["macros"].get("sodium"),
                calcium_mg=r["macros"].get("calcium"), potassium_mg=r["macros"].get("potassium"),
            ),
            allergens=r["allergens"], source_url=f"https://dsld.od.nih.gov/label/{r['id']}",
            trust=Trust(
                fda_registration_claimed=r["fda_reg"], gmp_claimed=r["gmp"],
                dshea_disclaimer_present=r["dshea"], third_party_tested_claimed=r["tpt"],
                certifications=[
                    Certification(
                        certifier=Certifier(c),
                        source_url=_CERT_SOURCE.get(c, f"https://dsld.od.nih.gov/label/{r['id']}"),
                        retrieved="2026-08-17",
                    )
                    for c in r.get("certs", [])
                ],
            ),
        )
        for name, unii, qty, unit in r["ingredients"]:
            p.ingredients.append(Ingredient(
                name=name, unii=unii, categories=categorise(name, unii),
                quantity=qty, unit=unit,
                is_proprietary_blend=looks_proprietary(name) or r.get("proprietary", False)
                and name.lower() in ("vegan protein blend", "complete protein blend",
                                      "arbonne protein matrix blend", "beflora soluble fiber",
                                      "bone broth matrix blend"),
            ))
        ds.products.append(p)
    return ds


if __name__ == "__main__":
    ds = build()
    out = Path("data")
    out.mkdir(exist_ok=True)
    (out / "sample_25.json").write_text(
        json.dumps(ds.model_dump(mode="json"), indent=2, default=str)
    )

    s = ds.summary()
    print(f"products: {s['total']}  (on market: {s['on_market']})")
    print(f"brands:   {s['brands']}")
    print(f"batch-tested for banned substances: {s['batch_tested']}")
    print(f"implies approval, unverified:       {s['implies_approval_only']}")
    print()
    print(f"{'BRAND':<24}{'PRODUCT':<52}{'PROTEIN%':>9}{'CERT':>10}")
    for p in sorted(ds.products, key=lambda p: p.brand):
        pct = p.protein_pct_by_weight
        pct_s = f"{pct}%" if pct is not None else "n/a"
        cert = "yes" if p.trust.has_independent_verification else (
            "unverif." if p.trust.implies_approval_without_verification else "-")
        print(f"{p.brand:<24}{p.name[:50]:<52}{pct_s:>9}{cert:>10}")

    print()
    gaps = unmapped(20)
    cov = coverage()
    print(f"taxonomy: {cov['unii_entries']} UNII + {cov['name_patterns']} name patterns, "
          f"{cov['unmapped_seen']} still gapped")
    for name, count in gaps:
        print(f"  {count}x  {name}")
