import { hasIndependentVerification, impliesApprovalWithoutVerification, trustState } from '../data/derived'
import { CERTIFIER_LABELS, CERT_SCOPE_LABELS, type Certifier, type Trust, type TrustState } from '../data/types'

const STYLES: Record<TrustState, string> = {
  verified: 'bg-verified-bg text-verified border-verified/30',
  'claim-only': 'bg-claim-bg text-claim border-claim/30',
  neutral: 'bg-code-bg text-ink-soft border-line-strong',
}

const DOT: Record<TrustState, string> = {
  verified: 'bg-verified',
  'claim-only': 'bg-claim',
  neutral: 'bg-ink-soft',
}

function label(state: TrustState, certifiers: Certifier[]): string {
  if (state === 'verified') {
    return certifiers.length === 1 ? CERTIFIER_LABELS[certifiers[0]] : `${certifiers.length} certifications`
  }
  if (state === 'claim-only') return 'Claims, no verification'
  return 'No certification claim'
}

/**
 * The compact badge, built from precomputed state rather than a full Trust
 * object — this is what a browse-grid card renders, and a card only has an
 * IndexRow (state + certifier list), not the full certification scopes that
 * live in a product's shard.
 */
export function StateBadge({
  state,
  certifiers,
  size = 'md',
}: {
  state: TrustState
  certifiers: Certifier[]
  size?: 'sm' | 'md'
}) {
  const sizeClasses = size === 'sm' ? 'text-[0.68rem] px-2 py-1' : 'text-[0.78rem] px-3 py-1.5'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-[3px] border font-mono uppercase tracking-wide ${sizeClasses} ${STYLES[state]}`}
    >
      <span className={`h-[7px] w-[7px] shrink-0 rounded-full ${DOT[state]}`} />
      {label(state, certifiers)}
    </span>
  )
}

/** Same badge, from a full Trust object — used on the product detail page,
 * which has the real certification list rather than just its state. */
export function TrustBadge({ trust, size = 'md' }: { trust: Trust; size?: 'sm' | 'md' }) {
  return (
    <StateBadge
      state={trustState(trust)}
      certifiers={trust.certifications.map((c) => c.certifier)}
      size={size}
    />
  )
}

/** Full breakdown for the product detail page -- every certifier + what it
 * actually covers, plus the claims that don't count as verification. */
export function TrustDetail({ trust }: { trust: Trust }) {
  const verified = hasIndependentVerification(trust)
  const claimOnly = impliesApprovalWithoutVerification(trust)

  return (
    <div className="space-y-4">
      <TrustBadge trust={trust} />

      {verified && (
        <ul className="space-y-2">
          {trust.certifications.map((cert, i) => (
            <li key={i} className="rounded border border-line bg-paper-raised p-3">
              <div className="font-serif text-[0.98rem] font-semibold text-ink">
                {CERTIFIER_LABELS[cert.certifier]}
              </div>
              <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.74rem] text-ink-soft">
                {cert.scopes.map((scope) => (
                  <li key={scope}>· {CERT_SCOPE_LABELS[scope]}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}

      {claimOnly && (
        <p className="border-l-2 border-claim bg-claim-bg px-3 py-2 text-[0.88rem] text-claim">
          This label references{' '}
          {trust.fda_registration_claimed && trust.gmp_claimed
            ? 'FDA registration and GMP compliance'
            : trust.fda_registration_claimed
              ? 'FDA registration'
              : 'GMP compliance'}
          , but carries no independent certification.
        </p>
      )}

      {!verified && !claimOnly && (
        <p className="text-[0.88rem] text-ink-soft">
          No certification or facility-approval claim on this label.
        </p>
      )}
    </div>
  )
}
