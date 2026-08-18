import { describe, expect, it } from 'vitest'
import { matchesFilters, matchesSearch, sortProducts } from './apply'
import { EMPTY_FILTERS, type Filters } from './types'
import type { Certifier, IndexRow } from '../data/types'

// ---------------------------------------------------------------------------
// Fixtures — IndexRow, not Product. matchesFilters/matchesSearch/sortProducts
// operate on the browse index (flat, precomputed fields), which is what
// actually gets filtered at ~117,800-row scale; Product (nested, full detail)
// is fetched lazily per-product on the detail page and never filtered.
// ---------------------------------------------------------------------------

function row(over: Partial<IndexRow> = {}): IndexRow {
  return {
    id: 1,
    brand: 'Brand',
    name: 'Product',
    category: 'vitamin',
    offMarket: false,
    proteinPct: null,
    trustState: 'neutral',
    certifiers: [],
    allergens: [],
    allergenDeclarationMissing: true,
    ingredientNames: [],
    hasArtificialSweetener: false,
    hasProprietaryBlend: false,
    shard: 0,
    ...over,
  }
}

const f = (over: Partial<Filters> = {}): Filters => ({ ...EMPTY_FILTERS, ...over })

// ---------------------------------------------------------------------------
// Certification: AND by default. This is the semantics change that prompted
// the whole review, so it is pinned from both directions.
// ---------------------------------------------------------------------------

describe('certification matching', () => {
  const both = row({
    trustState: 'verified',
    certifiers: ['informed_choice', 'informed_sport'],
  })
  const onlyChoice = row({ trustState: 'verified', certifiers: ['informed_choice'] })

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
    expect(matchesFilters(row(), f({ noCertOnly: true }))).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Allergens — the safety-critical filter
// ---------------------------------------------------------------------------

describe('allergen exclusion', () => {
  it('excludes on detected allergens, not just declared ones', () => {
    // The exact production bug: whey with no declaration used to pass.
    const undeclaredWhey = row({ allergens: ['milk'], allergenDeclarationMissing: true })
    expect(matchesFilters(undeclaredWhey, f({ excludeAllergens: ['milk'] }))).toBe(false)
  })

  it('keeps products with no trace of the allergen', () => {
    const pea = row({ allergens: [] })
    expect(matchesFilters(pea, f({ excludeAllergens: ['milk'] }))).toBe(true)
  })

  it('excludes every selected allergen, not just one of them', () => {
    const soyOnly = row({ allergens: ['soy'] })
    expect(matchesFilters(soyOnly, f({ excludeAllergens: ['milk', 'soy'] }))).toBe(false)
  })

  it('can additionally require that the label declares something', () => {
    const silent = row({ allergens: [], allergenDeclarationMissing: true })
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
  const withSucralose = row({ ingredientNames: ['Sucralose', 'Whey Protein'] })

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
    const peanut = row({ ingredientNames: ['Peanut Flour'] })
    expect(matchesFilters(peanut, f({ includeIngredients: ['pea'] }))).toBe(false)
    expect(matchesFilters(peanut, f({ includeIngredients: ['peanut'] }))).toBe(true)
  })

  it('matches mid-name words', () => {
    const p = row({ ingredientNames: ['organic Whey Protein concentrate'] })
    expect(matchesFilters(p, f({ includeIngredients: ['whey'] }))).toBe(true)
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
    const p = row({ brand: 'NutraBio' })
    expect(matchesFilters(p, f({ brands: ['NutraBio', 'GHOST'] }))).toBe(true)
    expect(matchesFilters(p, f({ brands: ['GHOST'] }))).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Protein threshold — must not treat "not comparable" as 0
// ---------------------------------------------------------------------------

describe('minimum protein', () => {
  it('keeps products above the threshold', () => {
    expect(matchesFilters(row({ proteinPct: 80 }), f({ minProteinPct: 70 }))).toBe(true)
  })
  it('drops products below it', () => {
    expect(matchesFilters(row({ proteinPct: 60 }), f({ minProteinPct: 70 }))).toBe(false)
  })
  it('drops products with no derivable figure rather than guessing', () => {
    expect(matchesFilters(row({ proteinPct: null }), f({ minProteinPct: 70 }))).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// On-market default
// ---------------------------------------------------------------------------

describe('on-market default', () => {
  it('hides off-market products by default', () => {
    const offMarket = row({ offMarket: true })
    expect(matchesFilters(offMarket, EMPTY_FILTERS)).toBe(false)
  })
  it('shows them when explicitly opted back in', () => {
    const offMarket = row({ offMarket: true })
    expect(matchesFilters(offMarket, f({ onMarketOnly: false }))).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

describe('search', () => {
  const p = row({ brand: 'NutraBio', name: 'Whey Isolate', ingredientNames: ['Sucralose'] })

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
  const certified = row({ id: 1, proteinPct: 50, trustState: 'verified' })
  const plain = row({ id: 2, proteinPct: 90 })
  const offMarket = row({ id: 3, proteinPct: 95, offMarket: true })
  const unknown = row({ id: 4, proteinPct: null })

  it('puts certified products first by default, then on-market, then off-market', () => {
    const ids = sortProducts([plain, offMarket, certified], 'trust').map((r) => r.id)
    expect(ids).toEqual([1, 2, 3])
  })

  it('sorts by protein descending', () => {
    const ids = sortProducts([certified, plain], 'protein-desc').map((r) => r.id)
    expect(ids).toEqual([2, 1])
  })

  it('sorts products with no protein figure last, not as zero', () => {
    const ids = sortProducts([unknown, certified], 'protein-desc').map((r) => r.id)
    expect(ids).toEqual([1, 4])
    const asc = sortProducts([unknown, certified], 'protein-asc').map((r) => r.id)
    expect(asc).toEqual([1, 4])
  })

  it('does not mutate the input array', () => {
    const input = [plain, certified]
    sortProducts(input, 'trust')
    expect(input.map((r) => r.id)).toEqual([2, 1])
  })
})

// ---------------------------------------------------------------------------
// Certifier list edge cases specific to IndexRow (flat certifiers array
// rather than Certification objects with scopes)
// ---------------------------------------------------------------------------

describe('certifiers array', () => {
  it('an empty certifiers array never satisfies a certification filter', () => {
    const p = row({ trustState: 'neutral', certifiers: [] })
    expect(matchesFilters(p, f({ certifiers: ['informed_sport' as Certifier] }))).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Group combination
// ---------------------------------------------------------------------------

describe('groups combine with AND', () => {
  it('requires every active facet to pass', () => {
    const p = row({
      brand: 'NutraBio',
      ingredientNames: ['Sucralose'],
      proteinPct: 80,
    })
    expect(matchesFilters(p, f({ brands: ['NutraBio'], minProteinPct: 70 }))).toBe(true)
    // same product, but now also required to be sucralose-free
    expect(
      matchesFilters(p, f({ brands: ['NutraBio'], minProteinPct: 70, excludeIngredients: ['sucralose'] })),
    ).toBe(false)
  })

  it('an empty filter set matches an on-market product', () => {
    expect(matchesFilters(row(), EMPTY_FILTERS)).toBe(true)
  })
})
