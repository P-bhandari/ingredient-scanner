import type { SortKey } from './apply'
import type { Certifier } from '../data/types'

/** How multiple selections within one facet combine. */
export type MatchMode = 'all' | 'any'

export interface Filters {
  includeIngredients: string[]
  ingredientMatchMode: MatchMode
  excludeIngredients: string[]
  certifiers: Certifier[]
  certMatchMode: MatchMode
  noCertOnly: boolean
  brands: string[]
  excludeAllergens: string[]
  /** Exclude products whose label declares no allergens at all. */
  requireAllergenDeclaration: boolean
  noArtificialSweetener: boolean
  noProprietaryBlend: boolean
  onMarketOnly: boolean
  minProteinPct: number | null
  sort: SortKey
}

export const EMPTY_FILTERS: Filters = {
  includeIngredients: [],
  ingredientMatchMode: 'all',
  excludeIngredients: [],
  certifiers: [],
  certMatchMode: 'all',
  noCertOnly: false,
  brands: [],
  excludeAllergens: [],
  requireAllergenDeclaration: false,
  noArtificialSweetener: false,
  noProprietaryBlend: false,
  // Off-market is 33% of the catalogue (130/396) and easy to miss behind a
  // small corner badge. Hiding it by default, with an explicit opt-in to see
  // it, matches what "browsing products" should mean; "onMarketOnly" is the
  // baseline, not a deviation from it.
  onMarketOnly: true,
  minProteinPct: null,
  sort: 'trust',
}

/**
 * Field-wise, not JSON.stringify. Stringify comparison depended on key
 * insertion order matching EMPTY_FILTERS, so any reordering spread or added
 * field would have broken "Clear all" silently.
 *
 * `sort` is deliberately excluded: changing the ordering isn't a filter, and
 * shouldn't light up the "Clear all" affordance.
 */
export function isEmpty(filters: Filters): boolean {
  return (
    filters.includeIngredients.length === 0 &&
    filters.excludeIngredients.length === 0 &&
    filters.certifiers.length === 0 &&
    filters.brands.length === 0 &&
    filters.excludeAllergens.length === 0 &&
    filters.noCertOnly === false &&
    filters.requireAllergenDeclaration === false &&
    filters.noArtificialSweetener === false &&
    filters.noProprietaryBlend === false &&
    // true is the default (hide off-market); false is the deviation, since
    // a user had to explicitly opt back in to see discontinued products.
    filters.onMarketOnly === true &&
    filters.minProteinPct == null
  )
}

/** Number of active filter criteria, for the "N active" affordance. */
export function activeCount(filters: Filters): number {
  return (
    filters.includeIngredients.length +
    filters.excludeIngredients.length +
    filters.certifiers.length +
    filters.brands.length +
    filters.excludeAllergens.length +
    (filters.noCertOnly ? 1 : 0) +
    (filters.requireAllergenDeclaration ? 1 : 0) +
    (filters.noArtificialSweetener ? 1 : 0) +
    (filters.noProprietaryBlend ? 1 : 0) +
    (filters.onMarketOnly === false ? 1 : 0) +
    (filters.minProteinPct != null ? 1 : 0)
  )
}

// ---------------------------------------------------------------------------
// URL round-trip
// ---------------------------------------------------------------------------

function listParam(sp: URLSearchParams, key: string): string[] {
  const v = sp.get(key)
  return v ? v.split(',').filter(Boolean) : []
}

function setListParam(sp: URLSearchParams, key: string, values: string[]) {
  if (values.length) sp.set(key, values.join(','))
  else sp.delete(key)
}

function setFlag(sp: URLSearchParams, key: string, on: boolean) {
  if (on) sp.set(key, '1')
  else sp.delete(key)
}

const SORT_KEYS: SortKey[] = ['trust', 'protein-desc', 'protein-asc', 'brand', 'name']

export function filtersFromParams(sp: URLSearchParams): Filters {
  const sort = sp.get('sort') as SortKey | null
  const minProtein = sp.get('minProtein')
  const parsedMin = minProtein != null ? Number(minProtein) : null

  return {
    includeIngredients: listParam(sp, 'inc'),
    ingredientMatchMode: sp.get('incMode') === 'any' ? 'any' : 'all',
    excludeIngredients: listParam(sp, 'exc'),
    certifiers: listParam(sp, 'certs') as Certifier[],
    certMatchMode: sp.get('certMode') === 'any' ? 'any' : 'all',
    noCertOnly: sp.get('noCert') === '1',
    brands: listParam(sp, 'brands'),
    excludeAllergens: listParam(sp, 'noAllergen'),
    requireAllergenDeclaration: sp.get('declaredOnly') === '1',
    noArtificialSweetener: sp.get('noSweetener') === '1',
    noProprietaryBlend: sp.get('noBlend') === '1',
    // Default true (hide off-market); "includeOffMarket=1" is the explicit
    // opt-out, so an ordinary URL with no filters applied doesn't need to
    // carry a param just to express the default.
    onMarketOnly: sp.get('includeOffMarket') !== '1',
    minProteinPct: parsedMin != null && Number.isFinite(parsedMin) ? parsedMin : null,
    sort: sort && SORT_KEYS.includes(sort) ? sort : 'trust',
  }
}

export function applyFiltersToParams(filters: Filters, base: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(base)
  setListParam(next, 'inc', filters.includeIngredients)
  setListParam(next, 'exc', filters.excludeIngredients)
  setListParam(next, 'certs', filters.certifiers)
  setListParam(next, 'brands', filters.brands)
  setListParam(next, 'noAllergen', filters.excludeAllergens)

  // Only serialise non-default modes, so ordinary URLs stay readable.
  if (filters.ingredientMatchMode === 'any') next.set('incMode', 'any')
  else next.delete('incMode')
  if (filters.certMatchMode === 'any') next.set('certMode', 'any')
  else next.delete('certMode')

  setFlag(next, 'noCert', filters.noCertOnly)
  setFlag(next, 'declaredOnly', filters.requireAllergenDeclaration)
  setFlag(next, 'noSweetener', filters.noArtificialSweetener)
  setFlag(next, 'noBlend', filters.noProprietaryBlend)
  setFlag(next, 'includeOffMarket', filters.onMarketOnly === false)

  if (filters.minProteinPct != null && Number.isFinite(filters.minProteinPct)) {
    next.set('minProtein', String(filters.minProteinPct))
  } else {
    next.delete('minProtein')
  }

  if (filters.sort !== 'trust') next.set('sort', filters.sort)
  else next.delete('sort')

  return next
}
