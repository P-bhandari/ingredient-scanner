// Client-side equivalents of the computed properties on labellens/schema.py's
// Trust/Macros/Product models. The source JSON is data, not behavior, so
// these are read as plain functions rather than methods.

import type { Product, Trust } from './types'

export function hasIndependentVerification(trust: Trust): boolean {
  return trust.certifications.length > 0
}

export function isBatchTestedForBannedSubstances(trust: Trust): boolean {
  return trust.certifications.some((c) => c.scopes.includes('banned_substances_every_batch'))
}

export function impliesApprovalWithoutVerification(trust: Trust): boolean {
  return (trust.fda_registration_claimed || trust.gmp_claimed) && !hasIndependentVerification(trust)
}

export type TrustState = 'verified' | 'claim-only' | 'neutral'

export function trustState(trust: Trust): TrustState {
  if (hasIndependentVerification(trust)) return 'verified'
  if (impliesApprovalWithoutVerification(trust)) return 'claim-only'
  return 'neutral'
}

/**
 * Protein as a percentage of serving weight, or null when no reliable figure
 * exists. Computed in the pipeline (labellens/schema.py) rather than here, so
 * one implementation is responsible for the unit handling and the data-quality
 * gate can assert on exactly what the site renders.
 *
 * Do NOT reintroduce a client-side calculation from `serving.quantity` — that
 * ignores the serving unit and is what produced "2500% protein by weight".
 */
export function proteinPctByWeight(product: Product): number | null {
  return product.protein_pct_by_weight
}

export function proteinPerCalorie(product: Product): number | null {
  const { protein_g, calories } = product.macros
  if (protein_g == null || !calories) return null
  return Math.round((protein_g / calories) * 10000) / 10000
}

export function hasArtificialSweetener(product: Product): boolean {
  return [...product.ingredients, ...product.other_ingredients].some((i) =>
    i.categories.includes('artificial_sweetener'),
  )
}

export function hasProprietaryBlend(product: Product): boolean {
  return [...product.ingredients, ...product.other_ingredients].some((i) => i.is_proprietary_blend)
}

export function allIngredients(product: Product) {
  return [...product.ingredients, ...product.other_ingredients]
}

/**
 * Allergens to filter and display on. Uses the declared + detected union,
 * because 44% of labels declare nothing while still containing dairy.
 */
export function allergensFor(product: Product): string[] {
  return product.allergens_all
}

export type AllergenStatus = 'declared' | 'detected' | 'undeclared'

/**
 * How we know about a given allergen — the distinction the UI must preserve.
 * "Not declared" is never the same claim as "free of".
 */
export function allergenStatus(product: Product, allergen: string): AllergenStatus | null {
  if (product.allergens.includes(allergen)) return 'declared'
  if (product.allergens_detected.includes(allergen)) return 'detected'
  return null
}

/** True when the label carries no allergen statement to rely on at all. */
export function allergenDataMissing(product: Product): boolean {
  return product.allergen_declaration_missing
}
