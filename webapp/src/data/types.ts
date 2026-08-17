// Mirrors labellens/schema.py. Kept in lockstep by hand -- the pipeline's
// pydantic models are the source of truth; this is a read-only view of their
// JSON serialization (data/dataset_full.json via prepare_data.py).

export type ProteinCategory = 'whey' | 'plant' | 'pea' | 'casein' | 'collagen'

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
  // --- computed by webapp/scripts/prepare_data.py from the pydantic model ---
  // Derived server-side so the client never has to guess what "1 Scoop"
  // weighs, and so the data-quality gate can assert on the same values the
  // site renders.

  /** Not part of the pydantic schema; joined from the pipeline's selection. */
  category: ProteinCategory
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

export interface Dataset {
  generated: string
  source_citation: string
  licence: string
  query: string
  products: Product[]
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

export const CATEGORY_LABELS: Record<ProteinCategory, string> = {
  whey: 'Whey',
  plant: 'Plant',
  pea: 'Pea',
  casein: 'Casein',
  collagen: 'Collagen',
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
