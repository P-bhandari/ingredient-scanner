import {
  allIngredients,
  hasArtificialSweetener,
  hasIndependentVerification,
  hasProprietaryBlend,
  proteinPctByWeight,
} from '../data/derived'
import type { Product } from '../data/types'
import type { Filters } from './types'

function ingredientNames(product: Product): string[] {
  return allIngredients(product).map((i) => i.name.toLowerCase())
}

/** AND across filter groups, OR within a group's own selections. */
export function matchesFilters(product: Product, filters: Filters): boolean {
  const names = ingredientNames(product)

  if (
    filters.includeIngredients.length &&
    !filters.includeIngredients.every((needle) => names.some((n) => n.includes(needle.toLowerCase())))
  ) {
    return false
  }

  if (
    filters.excludeIngredients.length &&
    filters.excludeIngredients.some((needle) => names.some((n) => n.includes(needle.toLowerCase())))
  ) {
    return false
  }

  if (
    filters.certifiers.length &&
    !product.trust.certifications.some((c) => filters.certifiers.includes(c.certifier))
  ) {
    return false
  }

  if (filters.noCertOnly && hasIndependentVerification(product.trust)) return false

  if (filters.brands.length && !filters.brands.includes(product.brand)) return false

  if (filters.excludeAllergens.length && filters.excludeAllergens.some((a) => product.allergens.includes(a))) {
    return false
  }

  if (filters.noArtificialSweetener && hasArtificialSweetener(product)) return false
  if (filters.noProprietaryBlend && hasProprietaryBlend(product)) return false
  if (filters.onMarketOnly && product.off_market) return false

  if (filters.minProteinPct != null) {
    const pct = proteinPctByWeight(product)
    if (pct == null || pct < filters.minProteinPct) return false
  }

  return true
}

export function matchesSearch(product: Product, query: string): boolean {
  if (!query.trim()) return true
  const q = query.trim().toLowerCase()
  return product.brand.toLowerCase().includes(q) || product.name.toLowerCase().includes(q)
}
