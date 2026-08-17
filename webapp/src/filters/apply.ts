import {
  allIngredients,
  allergensFor,
  hasArtificialSweetener,
  hasIndependentVerification,
  hasProprietaryBlend,
  proteinPctByWeight,
} from '../data/derived'
import type { Product } from '../data/types'
import type { Filters } from './types'

/**
 * Ingredient name matching.
 *
 * Whole words, not bare substrings: a raw `includes` makes "pea" match
 * "Peanut Flour" and "egg" match "eggplant". These filters drive allergen and
 * additive avoidance, where a wrong match in either direction is a real cost.
 *
 * A trailing `(s|es)?` keeps it usable — "flavor" should still find "Natural
 * Flavors" — without reopening the prefix hole that let "pea" match "peanut".
 */
function nameMatches(ingredientName: string, needle: string): boolean {
  const escaped = needle.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  if (!escaped) return false
  return new RegExp(`\\b${escaped}(s|es)?\\b`, 'i').test(ingredientName)
}

function matchesAnyIngredient(product: Product, needle: string): boolean {
  return allIngredients(product).some((i) => nameMatches(i.name, needle))
}

/**
 * Within-facet semantics follow the field's cardinality:
 *
 *   - A product holds a *set* of certifications and ingredients, so "has all
 *     of these" (AND) and "has any of these" (OR) are both meaningful. These
 *     honour the user's Any/All choice, defaulting to All.
 *   - A product has exactly *one* brand and one category, so AND across two
 *     selections is always empty. Those are necessarily OR.
 *   - Exclusions are always AND — "exclude all of these".
 *
 * Groups always combine with AND.
 */
export function matchesFilters(product: Product, filters: Filters): boolean {
  // --- has ingredient (multi-valued -> respects match mode) ---------------
  if (filters.includeIngredients.length) {
    const test = (needle: string) => matchesAnyIngredient(product, needle)
    const ok =
      filters.ingredientMatchMode === 'any'
        ? filters.includeIngredients.some(test)
        : filters.includeIngredients.every(test)
    if (!ok) return false
  }

  // --- does not have ingredient (exclusion -> always AND) -----------------
  if (filters.excludeIngredients.some((needle) => matchesAnyIngredient(product, needle))) {
    return false
  }

  // --- certification (multi-valued -> respects match mode) ----------------
  if (filters.certifiers.length) {
    const held = new Set(product.trust.certifications.map((c) => c.certifier))
    const ok =
      filters.certMatchMode === 'any'
        ? filters.certifiers.some((c) => held.has(c))
        : filters.certifiers.every((c) => held.has(c))
    if (!ok) return false
  }

  if (filters.noCertOnly && hasIndependentVerification(product.trust)) return false

  // --- brand (single-valued -> OR) ---------------------------------------
  if (filters.brands.length && !filters.brands.includes(product.brand)) return false

  // --- allergens (exclusion -> always AND) --------------------------------
  // Uses declared + detected. Filtering on the declaration alone let whey
  // products through an "exclude milk" filter.
  if (filters.excludeAllergens.length) {
    const present = allergensFor(product)
    if (filters.excludeAllergens.some((a) => present.includes(a))) return false
    // A label that declares nothing cannot support a "free of" claim. Opt-in
    // so the default stays permissive, but available to anyone who needs
    // certainty rather than silence.
    if (filters.requireAllergenDeclaration && product.allergen_declaration_missing) {
      return false
    }
  }

  // --- flags --------------------------------------------------------------
  if (filters.noArtificialSweetener && hasArtificialSweetener(product)) return false
  if (filters.noProprietaryBlend && hasProprietaryBlend(product)) return false
  if (filters.onMarketOnly && product.off_market) return false

  // --- macros -------------------------------------------------------------
  if (filters.minProteinPct != null) {
    const pct = proteinPctByWeight(product)
    if (pct == null || pct < filters.minProteinPct) return false
  }

  return true
}

export function matchesSearch(product: Product, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return (
    product.brand.toLowerCase().includes(q) ||
    product.name.toLowerCase().includes(q) ||
    // Searching ingredients is what people actually want from a label tool.
    allIngredients(product).some((i) => i.name.toLowerCase().includes(q))
  )
}

// ---------------------------------------------------------------------------
// Sorting
// ---------------------------------------------------------------------------

export type SortKey = 'trust' | 'protein-desc' | 'protein-asc' | 'brand' | 'name'

export const SORT_LABELS: Record<SortKey, string> = {
  trust: 'Certified first',
  'protein-desc': 'Protein % (high to low)',
  'protein-asc': 'Protein % (low to high)',
  brand: 'Brand (A–Z)',
  name: 'Name (A–Z)',
}

/**
 * Default is certified-first: on a site about the gap between real
 * verification and marketing claims, dataset order buries the products that
 * make the point. Products with no derivable protein % sort last rather than
 * being treated as 0%.
 */
export function sortProducts(products: Product[], key: SortKey): Product[] {
  const byProtein = (a: Product, b: Product, dir: 1 | -1) => {
    const av = proteinPctByWeight(a)
    const bv = proteinPctByWeight(b)
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    return (av - bv) * dir
  }

  const trustRank = (p: Product) =>
    hasIndependentVerification(p.trust) ? 0 : p.off_market ? 2 : 1

  return [...products].sort((a, b) => {
    switch (key) {
      case 'protein-desc':
        return byProtein(a, b, -1)
      case 'protein-asc':
        return byProtein(a, b, 1)
      case 'brand':
        return a.brand.localeCompare(b.brand) || a.name.localeCompare(b.name)
      case 'name':
        return a.name.localeCompare(b.name)
      case 'trust':
      default:
        return trustRank(a) - trustRank(b) || byProtein(a, b, -1)
    }
  })
}
