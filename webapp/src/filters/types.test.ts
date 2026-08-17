import { describe, expect, it } from 'vitest'
import {
  activeCount,
  applyFiltersToParams,
  EMPTY_FILTERS,
  filtersFromParams,
  isEmpty,
  type Filters,
} from './types'

const f = (over: Partial<Filters> = {}): Filters => ({ ...EMPTY_FILTERS, ...over })

describe('isEmpty', () => {
  it('is true for the empty filter set', () => {
    expect(isEmpty(EMPTY_FILTERS)).toBe(true)
  })

  it('is false once any facet is active', () => {
    expect(isEmpty(f({ certifiers: ['informed_sport'] }))).toBe(false)
    expect(isEmpty(f({ excludeAllergens: ['milk'] }))).toBe(false)
    expect(isEmpty(f({ minProteinPct: 0 }))).toBe(false)
  })

  it('treats hiding off-market as the default, and including it as the deviation', () => {
    // onMarketOnly: true is EMPTY_FILTERS' own value (off-market hidden by
    // default), so it must not make the set look "active."
    expect(isEmpty(f({ onMarketOnly: true }))).toBe(true)
    expect(isEmpty(f({ onMarketOnly: false }))).toBe(false)
  })

  it('ignores key order — the JSON.stringify comparison did not', () => {
    // Rebuilt with keys in a different insertion order. The old
    // implementation compared JSON strings and would have called this
    // non-empty, silently disabling "Clear all".
    const reordered = {
      sort: EMPTY_FILTERS.sort,
      minProteinPct: EMPTY_FILTERS.minProteinPct,
      onMarketOnly: EMPTY_FILTERS.onMarketOnly,
      noProprietaryBlend: EMPTY_FILTERS.noProprietaryBlend,
      noArtificialSweetener: EMPTY_FILTERS.noArtificialSweetener,
      requireAllergenDeclaration: EMPTY_FILTERS.requireAllergenDeclaration,
      excludeAllergens: [],
      brands: [],
      noCertOnly: false,
      certMatchMode: EMPTY_FILTERS.certMatchMode,
      certifiers: [],
      excludeIngredients: [],
      ingredientMatchMode: EMPTY_FILTERS.ingredientMatchMode,
      includeIngredients: [],
    } as Filters
    expect(isEmpty(reordered)).toBe(true)
  })

  it('does not treat sort as a filter', () => {
    expect(isEmpty(f({ sort: 'protein-desc' }))).toBe(true)
  })
})

describe('activeCount', () => {
  it('counts each selection, not each facet', () => {
    expect(activeCount(EMPTY_FILTERS)).toBe(0)
    expect(activeCount(f({ certifiers: ['informed_sport', 'informed_choice'] }))).toBe(2)
    // onMarketOnly: false is the deviation (opting back in to off-market
    // products), so it contributes to the count; the default (true) does not.
    expect(activeCount(f({ excludeAllergens: ['milk'], onMarketOnly: false }))).toBe(2)
    expect(activeCount(f({ onMarketOnly: true }))).toBe(0)
  })
})

describe('URL round-trip', () => {
  const cases: Array<[string, Filters]> = [
    ['empty', EMPTY_FILTERS],
    ['ingredients', f({ includeIngredients: ['stevia'], excludeIngredients: ['sucralose'] })],
    ['certifiers with mode', f({ certifiers: ['informed_sport'], certMatchMode: 'any' })],
    ['allergens', f({ excludeAllergens: ['milk', 'soy'], requireAllergenDeclaration: true })],
    ['flags', f({ noArtificialSweetener: true, noProprietaryBlend: true })],
    ['off-market opted back in', f({ onMarketOnly: false })],
    ['protein', f({ minProteinPct: 70 })],
    ['sort', f({ sort: 'protein-desc' })],
    ['brands', f({ brands: ['NutraBio', 'GHOST'] })],
  ]

  for (const [label, filters] of cases) {
    it(`survives a round-trip: ${label}`, () => {
      const params = applyFiltersToParams(filters, new URLSearchParams())
      expect(filtersFromParams(params)).toEqual(filters)
    })
  }

  it('preserves unrelated params such as category and search', () => {
    const base = new URLSearchParams({ category: 'whey', q: 'nutrabio' })
    const params = applyFiltersToParams(f({ noArtificialSweetener: true }), base)
    expect(params.get('category')).toBe('whey')
    expect(params.get('q')).toBe('nutrabio')
  })

  it('clears params when a filter is removed', () => {
    const withFilter = applyFiltersToParams(f({ noArtificialSweetener: true }), new URLSearchParams())
    expect(withFilter.get('noSweetener')).toBe('1')
    const cleared = applyFiltersToParams(EMPTY_FILTERS, withFilter)
    expect(cleared.get('noSweetener')).toBeNull()
  })

  describe('onMarketOnly default flip', () => {
    // Hiding off-market products is the baseline (see EMPTY_FILTERS), so an
    // ordinary URL shouldn't need a param to express it — only opting back
    // in should show up.
    it('the default (hidden) writes no param', () => {
      const params = applyFiltersToParams(f({ onMarketOnly: true }), new URLSearchParams())
      expect(params.get('includeOffMarket')).toBeNull()
    })

    it('opting back in writes an explicit param', () => {
      const params = applyFiltersToParams(f({ onMarketOnly: false }), new URLSearchParams())
      expect(params.get('includeOffMarket')).toBe('1')
    })

    it('a URL with no params at all defaults to hiding off-market', () => {
      expect(filtersFromParams(new URLSearchParams()).onMarketOnly).toBe(true)
    })
  })

  it('keeps default modes out of the URL', () => {
    const params = applyFiltersToParams(f({ certifiers: ['informed_sport'] }), new URLSearchParams())
    expect(params.get('certMode')).toBeNull()
    expect(params.get('sort')).toBeNull()
  })

  it('ignores a malformed sort key', () => {
    expect(filtersFromParams(new URLSearchParams({ sort: 'nonsense' })).sort).toBe('trust')
  })

  it('ignores a non-numeric protein minimum', () => {
    expect(filtersFromParams(new URLSearchParams({ minProtein: 'abc' })).minProteinPct).toBeNull()
  })
})
