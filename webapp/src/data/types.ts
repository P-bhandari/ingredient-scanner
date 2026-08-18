// Mirrors labellens/schema.py. Kept in lockstep by hand -- the pipeline's
// pydantic models are the source of truth; this is a read-only view of their
// JSON serialization (data/dataset_supplements_full.json via
// webapp/scripts/prepare_full_catalogue.py).

// DSLD's own product_type classification (11 values across the full ~118k
// corpus), not a hand-built taxonomy -- see prepare_full_catalogue.py for
// why. "uncategorized" only exists as a safety net; the build fails loudly
// if any real product actually lands there.
export type ProductCategory =
  | 'other_combinations'
  | 'botanical'
  | 'non_nutrient'
  | 'botanical_with_nutrients'
  | 'vitamin'
  | 'amino_acid_protein'
  | 'fat_fatty_acid'
  | 'mineral'
  | 'multivitamin_mineral'
  | 'single_vitamin_mineral'
  | 'fiber_other'
  | 'uncategorized'

export type IngredientCategory =
  | 'protein_source'
  | 'artificial_sweetener'
  | 'natural_sweetener'
  | 'added_sugar'
  | 'thickener_emulsifier'
  | 'filler_bulking'
  | 'digestive_enzyme'
  | 'flavour_colour'
  | 'vitamin'
  | 'mineral'
  | 'amino_acid'
  | 'stimulant'
  | 'allergen_source'
  | 'macro'
  | 'other'

export type Certifier =
  | 'nsf_certified_for_sport'
  | 'nsf_contents_certified'
  | 'informed_sport'
  | 'informed_choice'
  | 'usp_verified'
  | 'bscg'

export type CertScope =
  | 'banned_substances_every_batch'
  | 'label_accuracy'
  | 'contaminants'
  | 'process_only'

export type TrustState = 'verified' | 'claim-only' | 'neutral'

export interface Certification {
  certifier: Certifier
  scopes: CertScope[]
  match_confidence: number
  source_url: string
  retrieved: string
}

export interface Trust {
  certifications: Certification[]
  gmp_claimed: boolean
  fda_registration_claimed: boolean
  third_party_tested_claimed: boolean
  dshea_disclaimer_present: boolean
}

export interface Ingredient {
  name: string
  unii: string | null
  dsld_category: string | null
  categories: IngredientCategory[]
  quantity: number | null
  unit: string | null
  percent_dv: number | null
  depth: number
  is_proprietary_blend: boolean
}

export interface Macros {
  calories: number | null
  protein_g: number | null
  total_fat_g: number | null
  saturated_fat_g: number | null
  cholesterol_mg: number | null
  total_carbs_g: number | null
  sugar_g: number | null
  added_sugar_g: number | null
  fibre_g: number | null
  sodium_mg: number | null
  calcium_mg: number | null
  potassium_mg: number | null
}

export interface NutrientPanelEntry {
  name: string
  quantity: number | null
  unit: string | null
  percent_dv: number | null
}

export interface Serving {
  quantity: number | null
  /** Upper bound for range servings ("1-2 scoops"). */
  max_quantity: number | null
  unit: string | null
  note: string | null
  per_container: string | null
}

/**
 * The full per-product record, one per shard file
 * (public/data/shards/<id % 360>.json). Fetched lazily by the product detail
 * page only -- at ~117,800 products this cannot be a JS-bundled or
 * eagerly-fetched dataset the way the 396-product protein catalogue was.
 */
export interface Product {
  dsld_id: number
  brand: string
  name: string
  upc: string | null
  off_market: boolean
  entry_date: string | null
  physical_state: string | null
  product_type: string | null
  serving: Serving
  macros: Macros
  ingredients: Ingredient[]
  other_ingredients: Ingredient[]
  nutrient_panel: NutrientPanelEntry[]
  /** Allergens the label explicitly declares. */
  allergens: string[]
  /** Allergens implied by the ingredient list (44% of labels declare none). */
  allergens_detected: string[]
  target_groups: string[]
  trust: Trust
  manufacturer: string | null
  manufacturer_country: string | null
  source: string
  source_url: string | null
  // --- computed server-side by prepare_full_catalogue.py from the pydantic
  // model, so the client never has to guess what "1 Scoop" weighs, and the
  // data-quality gate can assert on the same values the site renders.
  category: ProductCategory
  /** null when no reliable figure exists (non-mass or inconsistent serving). */
  protein_pct_by_weight: number | null
  /** Which serving figure the percentage used. */
  protein_pct_basis: 'declared' | 'max_serving' | null
  serving_grams: number | null
  /** Declared and detected, unioned. What filters act on. */
  allergens_all: string[]
  /** True when the label declares nothing — never read this as "free of". */
  allergen_declaration_missing: boolean
}

/**
 * One row per product in public/data/index.json (~118k rows, ~60MB / ~7.6MB
 * gzipped). Everything browsing, filtering, sorting, searching, and a
 * product card need, precomputed at build time — flat fields rather than the
 * nested nutrient/trust/ingredient structures on Product, both because most
 * of that detail is irrelevant to a list view and because recomputing
 * derived values (protein %, trust state, allergen union) from nested data
 * on every filter keystroke across 118k rows is real, avoidable cost.
 */
export interface IndexRow {
  id: number
  brand: string
  name: string
  category: ProductCategory
  offMarket: boolean
  proteinPct: number | null
  trustState: TrustState
  certifiers: Certifier[]
  /** Declared + detected allergens, unioned (same as Product.allergens_all). */
  allergens: string[]
  allergenDeclarationMissing: boolean
  /** Flat ingredient names only (no categories/quantities — see Product for those). */
  ingredientNames: string[]
  hasArtificialSweetener: boolean
  hasProprietaryBlend: boolean
  /** Which shard file (public/data/shards/<shard>.json) holds the full Product. */
  shard: number
}

export interface CatalogueMeta {
  generated: string
  sourceCitation: string
  licence: string
  productCount: number
  shardCount: number
}

/**
 * Autocomplete option lists (public/data/facets.json), precomputed at build
 * time. Building these by scanning every ingredientNames array across
 * ~117,800 index rows client-side blocked the main thread for tens of
 * seconds — an aggregate over the whole corpus belongs in the batch build.
 */
export interface Facets {
  ingredientNames: string[]
  brands: string[]
}

export const CERTIFIER_LABELS: Record<Certifier, string> = {
  nsf_certified_for_sport: 'NSF Certified for Sport',
  nsf_contents_certified: 'NSF Contents Certified',
  informed_sport: 'Informed Sport',
  informed_choice: 'Informed Choice',
  usp_verified: 'USP Verified',
  bscg: 'BSCG Certified Drug Free',
}

export const CERT_SCOPE_LABELS: Record<CertScope, string> = {
  banned_substances_every_batch: 'Every batch tested for banned substances',
  label_accuracy: 'Label accuracy verified',
  contaminants: 'Contaminant screening',
  process_only: 'Manufacturing process reviewed',
}

// Order here is nav order. "Other Combinations" is DSLD's largest single
// bucket (~36% of the corpus, mixed multi-ingredient formulas that don't fit
// its other categories) and is placed last deliberately -- it's real data,
// but not what most people mean when they say "browse by category."
export const CATEGORY_ORDER: ProductCategory[] = [
  'vitamin',
  'mineral',
  'multivitamin_mineral',
  'single_vitamin_mineral',
  'amino_acid_protein',
  'botanical',
  'botanical_with_nutrients',
  'fat_fatty_acid',
  'fiber_other',
  'non_nutrient',
  'other_combinations',
  'uncategorized',
]

export const CATEGORY_LABELS: Record<ProductCategory, string> = {
  vitamin: 'Vitamins',
  mineral: 'Minerals',
  multivitamin_mineral: 'Multivitamin & Mineral',
  single_vitamin_mineral: 'Single Vitamin or Mineral',
  amino_acid_protein: 'Amino Acid / Protein',
  botanical: 'Botanical',
  botanical_with_nutrients: 'Botanical with Nutrients',
  fat_fatty_acid: 'Fat / Fatty Acid',
  fiber_other: 'Fiber & Other Nutrients',
  non_nutrient: 'Non-Nutrient / Non-Botanical',
  other_combinations: 'Other Combinations',
  uncategorized: 'Uncategorized',
}

export const INGREDIENT_CATEGORY_LABELS: Record<IngredientCategory, string> = {
  protein_source: 'Protein source',
  artificial_sweetener: 'Artificial sweetener',
  natural_sweetener: 'Natural sweetener',
  added_sugar: 'Added sugar',
  thickener_emulsifier: 'Thickener / emulsifier',
  filler_bulking: 'Filler / bulking agent',
  digestive_enzyme: 'Digestive enzyme',
  flavour_colour: 'Flavour / colour',
  vitamin: 'Vitamin',
  mineral: 'Mineral',
  amino_acid: 'Amino acid',
  stimulant: 'Stimulant',
  allergen_source: 'Allergen source',
  macro: 'Macro',
  other: 'Other',
}
