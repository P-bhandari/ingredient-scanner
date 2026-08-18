import { Link } from 'react-router-dom'
import { CATEGORY_LABELS, type IndexRow } from '../data/types'
import { FavoriteButton } from './FavoriteButton'
import { ProductPhoto } from './ProductPhoto'
import { StateBadge } from './TrustBadge'

export function ProductCard({ row }: { row: IndexRow }) {
  // Most of the catalogue carries no certification claim at all — showing a
  // badge for that on every card makes badges mean nothing. Only the two
  // states worth a second look (verified, or claiming without verification)
  // get one; silence is the default.
  const showBadge = row.trustState !== 'neutral'

  return (
    <Link
      to={`/product/${row.id}`}
      className={`group flex flex-col overflow-hidden rounded-md border border-line bg-paper-raised transition-shadow hover:shadow-[0_2px_14px_rgba(0,0,0,0.06)] ${
        row.offMarket ? 'opacity-55 hover:opacity-90' : ''
      }`}
    >
      <div className="relative">
        <ProductPhoto brand={row.brand} className="aspect-square w-full text-3xl" />
        <div className="absolute right-2 top-2 rounded-full bg-paper-raised/90 backdrop-blur-sm">
          <FavoriteButton dsldId={row.id} size="sm" />
        </div>
        {row.offMarket && (
          <span className="absolute left-2 top-2 rounded bg-ink px-1.5 py-0.5 font-mono text-[0.62rem] uppercase tracking-wide text-paper-raised">
            Off market
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-3.5">
        <span className="font-mono text-[0.68rem] uppercase tracking-wide text-ink-soft">
          {row.brand} · {CATEGORY_LABELS[row.category]}
        </span>
        <h3 className="font-serif text-[0.98rem] font-semibold leading-snug text-ink group-hover:text-accent">
          {row.name}
        </h3>
        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          {row.proteinPct != null ? (
            <span className="font-mono text-[0.78rem] tabular-nums text-ink-soft">{row.proteinPct}% protein</span>
          ) : (
            <span />
          )}
          {showBadge && <StateBadge state={row.trustState} certifiers={row.certifiers} size="sm" />}
        </div>
      </div>
    </Link>
  )
}
