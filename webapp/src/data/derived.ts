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

export function proteinPctByWeight(product: Product): number | null {
  const { protein_g } = product.macros
  const servingQty = product.serving.quantity
  if (protein_g == null || !servingQty) return null
  return Math.round((100 * protein_g) / servingQty * 10) / 10
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
