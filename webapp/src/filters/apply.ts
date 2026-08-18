import type { Certifier, IndexRow } from '../data/types'
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

function matchesAnyIngredient(row: IndexRow, needle: string): boolean {
  return row.ingredientNames.some((name) => nameMatches(name, needle))
}

/** The certification constraint in isolation — shared by matchesFilters and
 * the facet-count fast path below, which needs to test it against a
 * certifier list that isn't necessarily `filters.certifiers` itself. */
export function certifierConstraintSatisfied(
  row: IndexRow,
  certifiers: readonly Certifier[],
  mode: 'any' | 'all',
): boolean {
  const held = new Set(row.certifiers)
  return mode === 'any' ? certifiers.some((c) => held.has(c)) : certifiers.every((c) => held.has(c))
}

/** The allergen-exclusion constraint in isolation, for the same reason. */
export function allergenConstraintSatisfied(
  row: IndexRow,
  excludeAllergens: readonly string[],
  requireDeclaration: boolean,
): boolean {
  if (excludeAllergens.some((a) => row.allergens.includes(a))) return false
  if (requireDeclaration && row.allergenDeclarationMissing) return false
  return true
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
 *
 * Operates on IndexRow, not Product: at ~117,800 rows this runs on every
 * keystroke, and IndexRow's fields are already flat and precomputed
 * (protein %, trust state, allergen union) rather than nested structures that
 * would need re-deriving on every pass.
 *
 * `except` skips one dimension's check entirely. It exists so the facet-count
 * computation in BrowsePage can compute "passes everything except
 * certifiers" once and reuse it across all six certifier options, rather
 * than re-running the full gauntlet — ingredients, brand, allergens, flags —
 * once per option. matchesFilters itself is just this with nothing excluded.
 */
export function matchesFiltersExcept(
  row: IndexRow,
  filters: Filters,
  except: 'certifiers' | 'allergens' | 'none',
): boolean {
  // --- has ingredient (multi-valued -> respects match mode) ---------------
  if (filters.includeIngredients.length) {
    const test = (needle: string) => matchesAnyIngredient(row, needle)
    const ok =
      filters.ingredientMatchMode === 'any'
        ? filters.includeIngredients.some(test)
        : filters.includeIngredients.every(test)
    if (!ok) return false
  }

  // --- does not have ingredient (exclusion -> always AND) -----------------
  if (filters.excludeIngredients.some((needle) => matchesAnyIngredient(row, needle))) {
    return false
  }

  // --- certification (multi-valued -> respects match mode) ----------------
  if (except !== 'certifiers') {
    if (filters.certifiers.length && !certifierConstraintSatisfied(row, filters.certifiers, filters.certMatchMode)) {
      return false
    }
    if (filters.noCertOnly && row.trustState === 'verified') return false
  }

  // --- brand (single-valued -> OR) ---------------------------------------
  if (filters.brands.length && !filters.brands.includes(row.brand)) return false

  // --- allergens (exclusion -> always AND) --------------------------------
  // Uses declared + detected. Filtering on the declaration alone let whey
  // products through an "exclude milk" filter.
  if (except !== 'allergens') {
    if (
      filters.excludeAllergens.length &&
      !allergenConstraintSatisfied(row, filters.excludeAllergens, filters.requireAllergenDeclaration)
    ) {
      return false
    }
  }

  // --- flags --------------------------------------------------------------
  if (filters.noArtificialSweetener && row.hasArtificialSweetener) return false
  if (filters.noProprietaryBlend && row.hasProprietaryBlend) return false
  if (filters.onMarketOnly && row.offMarket) return false

  // --- macros -------------------------------------------------------------
  if (filters.minProteinPct != null) {
    if (row.proteinPct == null || row.proteinPct < filters.minProteinPct) return false
  }

  return true
}

export function matchesFilters(row: IndexRow, filters: Filters): boolean {
  return matchesFiltersExcept(row, filters, 'none')
}

export function matchesSearch(row: IndexRow, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return (
    row.brand.toLowerCase().includes(q) ||
    row.name.toLowerCase().includes(q) ||
    // Searching ingredients is what people actually want from a label tool.
    row.ingredientNames.some((name) => name.toLowerCase().includes(q))
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
export function sortProducts(rows: IndexRow[], key: SortKey): IndexRow[] {
  const byProtein = (a: IndexRow, b: IndexRow, dir: 1 | -1) => {
    if (a.proteinPct == null && b.proteinPct == null) return 0
    if (a.proteinPct == null) return 1
    if (b.proteinPct == null) return -1
    return (a.proteinPct - b.proteinPct) * dir
  }

  const trustRank = (row: IndexRow) => (row.trustState === 'verified' ? 0 : row.offMarket ? 2 : 1)

  return [...rows].sort((a, b) => {
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
