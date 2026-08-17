import { describe, expect, it } from 'vitest'
import { matchesFilters, matchesSearch, sortProducts } from './apply'
import { EMPTY_FILTERS, type Filters } from './types'
import type { Certification, Certifier, Ingredient, Product } from '../data/types'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function ingredient(name: string, extra: Partial<Ingredient> = {}): Ingredient {
  return {
    name,
    unii: null,
    dsld_category: null,
    categories: [],
    quantity: null,
    unit: null,
    percent_dv: null,
    depth: 0,
    is_proprietary_blend: false,
    ...extra,
  }
}

function cert(certifier: Certifier): Certification {
  return { certifier, scopes: [], match_confidence: 1, source_url: '', retrieved: '' }
}

function product(over: Partial<Product> = {}): Product {
  return {
    dsld_id: 1,
    brand: 'Brand',
    name: 'Product',
    upc: null,
    off_market: false,
    entry_date: null,
    physical_state: null,
    product_type: null,
    serving: { quantity: 30, max_quantity: null, unit: 'Gram(s)', note: null, per_container: null },
    macros: {
      calories: null, protein_g: null, total_fat_g: null, saturated_fat_g: null,
      cholesterol_mg: null, total_carbs_g: null, sugar_g: null, added_sugar_g: null,
      fibre_g: null, sodium_mg: null, calcium_mg: null, potassium_mg: null,
    },
    ingredients: [],
    other_ingredients: [],
    nutrient_panel: [],
    allergens: [],
    allergens_detected: [],
    target_groups: [],
    trust: {
      certifications: [],
      gmp_claimed: false,
      fda_registration_claimed: false,
      third_party_tested_claimed: false,
      dshea_disclaimer_present: false,
    },
    manufacturer: null,
    manufacturer_country: null,
    source: 'DSLD',
    source_url: null,
    category: 'whey',
    protein_pct_by_weight: null,
    protein_pct_basis: null,
    serving_grams: 30,
    allergens_all: [],
    allergen_declaration_missing: true,
    ...over,
  }
}

const f = (over: Partial<Filters> = {}): Filters => ({ ...EMPTY_FILTERS, ...over })

// ---------------------------------------------------------------------------
// Certification: AND by default. This is the semantics change that prompted
// the whole review, so it is pinned from both directions.
// ---------------------------------------------------------------------------

describe('certification matching', () => {
  const both = product({
    trust: { ...product().trust, certifications: [cert('informed_choice'), cert('informed_sport')] },
  })
  const onlyChoice = product({
    trust: { ...product().trust, certifications: [cert('informed_choice')] },
  })

  it('requires ALL selected certifiers by default', () => {
    const filters = f({ certifiers: ['informed_choice', 'informed_sport'] })
    expect(matchesFilters(both, filters)).toBe(true)
    expect(matchesFilters(onlyChoice, filters)).toBe(false)
  })

  it('requires only one when the mode is "any"', () => {
    const filters = f({ certifiers: ['informed_choice', 'informed_sport'], certMatchMode: 'any' })
    expect(matchesFilters(both, filters)).toBe(true)
    expect(matchesFilters(onlyChoice, filters)).toBe(true)
  })

  it('a single selection behaves the same in both modes', () => {
    for (const mode of ['all', 'any'] as const) {
      const filters = f({ certifiers: ['informed_choice'], certMatchMode: mode })
      expect(matchesFilters(onlyChoice, filters)).toBe(true)
    }
  })

  it('noCertOnly excludes anything independently certified', () => {
    expect(matchesFilters(onlyChoice, f({ noCertOnly: true }))).toBe(false)
    expect(matchesFilters(product(), f({ noCertOnly: true }))).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Allergens — the safety-critical filter
// ---------------------------------------------------------------------------

describe('allergen exclusion', () => {
  it('excludes on detected allergens, not just declared ones', () => {
    // The exact production bug: whey with no declaration used to pass.
    const undeclaredWhey = product({
      ingredients: [ingredient('Whey Protein Concentrate')],
      allergens: [],
      allergens_detected: ['milk'],
      allergens_all: ['milk'],
      allergen_declaration_missing: true,
    })
    expect(matchesFilters(undeclaredWhey, f({ excludeAllergens: ['milk'] }))).toBe(false)
  })

  it('keeps products with no trace of the allergen', () => {
    const pea = product({ allergens_all: [], allergens_detected: [] })
    expect(matchesFilters(pea, f({ excludeAllergens: ['milk'] }))).toBe(true)
  })

  it('excludes every selected allergen, not just one of them', () => {
    const soyOnly = product({ allergens_all: ['soy'] })
    expect(matchesFilters(soyOnly, f({ excludeAllergens: ['milk', 'soy'] }))).toBe(false)
  })

  it('can additionally require that the label declares something', () => {
    const silent = product({ allergens_all: [], allergen_declaration_missing: true })
    expect(matchesFilters(silent, f({ excludeAllergens: ['milk'] }))).toBe(true)
    expect(
      matchesFilters(silent, f({ excludeAllergens: ['milk'], requireAllergenDeclaration: true })),
    ).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Ingredient matching
// ---------------------------------------------------------------------------

describe('ingredient matching', () => {
  const withSucralose = product({ ingredients: [ingredient('Sucralose'), ingredient('Whey Protein')] })

  it('requires all listed ingredients by default', () => {
    expect(matchesFilters(withSucralose, f({ includeIngredients: ['sucralose', 'whey'] }))).toBe(true)
    expect(matchesFilters(withSucralose, f({ includeIngredients: ['sucralose', 'stevia'] }))).toBe(false)
  })

  it('honours "any" mode', () => {
    const filters = f({ includeIngredients: ['sucralose', 'stevia'], ingredientMatchMode: 'any' })
    expect(matchesFilters(withSucralose, filters)).toBe(true)
  })

  it('excludes on any listed ingredient', () => {
    expect(matchesFilters(withSucralose, f({ excludeIngredients: ['sucralose'] }))).toBe(false)
  })

  it('matches on word boundaries, so "pea" does not match "peanut"', () => {
    const peanut = product({ ingredients: [ingredient('Peanut Flour')] })
    expect(matchesFilters(peanut, f({ includeIngredients: ['pea'] }))).toBe(false)
    expect(matchesFilters(peanut, f({ includeIngredients: ['peanut'] }))).toBe(true)
  })

  it('matches mid-name words', () => {
    const p = product({ ingredients: [ingredient('organic Whey Protein concentrate')] })
    expect(matchesFilters(p, f({ includeIngredients: ['whey'] }))).toBe(true)
  })

  it('searches other_ingredients too (43% of products keep them there)', () => {
    const p = product({ ingredients: [], other_ingredients: [ingredient('Stevia extract')] })
    expect(matchesFilters(p, f({ includeIngredients: ['stevia'] }))).toBe(true)
  })

  it('does not crash on regex metacharacters', () => {
    expect(() => matchesFilters(withSucralose, f({ includeIngredients: ['('] }))).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// Single-valued facets must be OR — AND would always be empty
// ---------------------------------------------------------------------------

describe('brand', () => {
  it('matches any of the selected brands', () => {
    const p = product({ brand: 'NutraBio' })
    expect(matchesFilters(p, f({ brands: ['NutraBio', 'GHOST'] }))).toBe(true)
    expect(matchesFilters(p, f({ brands: ['GHOST'] }))).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Protein threshold — must not treat "not comparable" as 0
// ---------------------------------------------------------------------------

describe('minimum protein', () => {
  it('keeps products above the threshold', () => {
    expect(matchesFilters(product({ protein_pct_by_weight: 80 }), f({ minProteinPct: 70 }))).toBe(true)
  })
  it('drops products below it', () => {
    expect(matchesFilters(product({ protein_pct_by_weight: 60 }), f({ minProteinPct: 70 }))).toBe(false)
  })
  it('drops products with no derivable figure rather than guessing', () => {
    expect(matchesFilters(product({ protein_pct_by_weight: null }), f({ minProteinPct: 70 }))).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

describe('search', () => {
  const p = product({ brand: 'NutraBio', name: 'Whey Isolate', ingredients: [ingredient('Sucralose')] })

  it('matches brand and name case-insensitively', () => {
    expect(matchesSearch(p, 'nutrabio')).toBe(true)
    expect(matchesSearch(p, 'ISOLATE')).toBe(true)
  })
  it('matches ingredients', () => {
    expect(matchesSearch(p, 'sucralose')).toBe(true)
  })
  it('returns everything for an empty query', () => {
    expect(matchesSearch(p, '   ')).toBe(true)
  })
  it('does not match unrelated text', () => {
    expect(matchesSearch(p, 'creatine')).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Sorting
// ---------------------------------------------------------------------------

describe('sorting', () => {
  const certified = product({
    dsld_id: 1,
    protein_pct_by_weight: 50,
    trust: { ...product().trust, certifications: [cert('informed_sport')] },
  })
  const plain = product({ dsld_id: 2, protein_pct_by_weight: 90 })
  const offMarket = product({ dsld_id: 3, protein_pct_by_weight: 95, off_market: true })
  const unknown = product({ dsld_id: 4, protein_pct_by_weight: null })

  it('puts certified products first by default, then on-market, then off-market', () => {
    const ids = sortProducts([plain, offMarket, certified], 'trust').map((p) => p.dsld_id)
    expect(ids).toEqual([1, 2, 3])
  })

  it('sorts by protein descending', () => {
    const ids = sortProducts([certified, plain], 'protein-desc').map((p) => p.dsld_id)
    expect(ids).toEqual([2, 1])
  })

  it('sorts products with no protein figure last, not as zero', () => {
    const ids = sortProducts([unknown, certified], 'protein-desc').map((p) => p.dsld_id)
    expect(ids).toEqual([1, 4])
    const asc = sortProducts([unknown, certified], 'protein-asc').map((p) => p.dsld_id)
    expect(asc).toEqual([1, 4])
  })

  it('does not mutate the input array', () => {
    const input = [plain, certified]
    sortProducts(input, 'trust')
    expect(input.map((p) => p.dsld_id)).toEqual([2, 1])
  })
})

// ---------------------------------------------------------------------------
// Group combination
// ---------------------------------------------------------------------------

describe('groups combine with AND', () => {
  it('requires every active facet to pass', () => {
    const p = product({
      brand: 'NutraBio',
      ingredients: [ingredient('Sucralose')],
      protein_pct_by_weight: 80,
    })
    expect(matchesFilters(p, f({ brands: ['NutraBio'], minProteinPct: 70 }))).toBe(true)
    // same product, but now also required to be sucralose-free
    expect(
      matchesFilters(p, f({ brands: ['NutraBio'], minProteinPct: 70, excludeIngredients: ['sucralose'] })),
    ).toBe(false)
  })

  it('an empty filter set matches everything', () => {
    expect(matchesFilters(product(), EMPTY_FILTERS)).toBe(true)
  })
})
