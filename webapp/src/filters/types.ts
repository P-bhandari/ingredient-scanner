import type { Certifier } from '../data/types'

export interface Filters {
  includeIngredients: string[]
  excludeIngredients: string[]
  certifiers: Certifier[]
  noCertOnly: boolean
  brands: string[]
  excludeAllergens: string[]
  noArtificialSweetener: boolean
  noProprietaryBlend: boolean
  onMarketOnly: boolean
  minProteinPct: number | null
}

export const EMPTY_FILTERS: Filters = {
  includeIngredients: [],
  excludeIngredients: [],
  certifiers: [],
  noCertOnly: false,
  brands: [],
  excludeAllergens: [],
  noArtificialSweetener: false,
  noProprietaryBlend: false,
  onMarketOnly: false,
  minProteinPct: null,
}

export function isEmpty(filters: Filters): boolean {
  return JSON.stringify(filters) === JSON.stringify(EMPTY_FILTERS)
}

function listParam(sp: URLSearchParams, key: string): string[] {
  const v = sp.get(key)
  return v ? v.split(',').filter(Boolean) : []
}

function setListParam(sp: URLSearchParams, key: string, values: string[]) {
  if (values.length) sp.set(key, values.join(','))
  else sp.delete(key)
}

export function filtersFromParams(sp: URLSearchParams): Filters {
  return {
    includeIngredients: listParam(sp, 'inc'),
    excludeIngredients: listParam(sp, 'exc'),
    certifiers: listParam(sp, 'certs') as Certifier[],
    noCertOnly: sp.get('noCert') === '1',
    brands: listParam(sp, 'brands'),
    excludeAllergens: listParam(sp, 'noAllergen'),
    noArtificialSweetener: sp.get('noSweetener') === '1',
    noProprietaryBlend: sp.get('noBlend') === '1',
    onMarketOnly: sp.get('onMarket') === '1',
    minProteinPct: sp.get('minProtein') ? Number(sp.get('minProtein')) : null,
  }
}

export function applyFiltersToParams(filters: Filters, base: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(base)
  setListParam(next, 'inc', filters.includeIngredients)
  setListParam(next, 'exc', filters.excludeIngredients)
  setListParam(next, 'certs', filters.certifiers)
  if (filters.noCertOnly) next.set('noCert', '1')
  else next.delete('noCert')
  setListParam(next, 'brands', filters.brands)
  setListParam(next, 'noAllergen', filters.excludeAllergens)
  if (filters.noArtificialSweetener) next.set('noSweetener', '1')
  else next.delete('noSweetener')
  if (filters.noProprietaryBlend) next.set('noBlend', '1')
  else next.delete('noBlend')
  if (filters.onMarketOnly) next.set('onMarket', '1')
  else next.delete('onMarket')
  if (filters.minProteinPct != null && !Number.isNaN(filters.minProteinPct)) {
    next.set('minProtein', String(filters.minProteinPct))
  } else {
    next.delete('minProtein')
  }
  return next
}
