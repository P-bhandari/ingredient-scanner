import { Link } from 'react-router-dom'
import { proteinPctByWeight } from '../data/derived'
import { CATEGORY_LABELS, type Product } from '../data/types'
import { FavoriteButton } from './FavoriteButton'
import { ProductPhoto } from './ProductPhoto'
import { TrustBadge } from './TrustBadge'

export function ProductCard({ product }: { product: Product }) {
  const pct = proteinPctByWeight(product)

  return (
    <Link
      to={`/product/${product.dsld_id}`}
      className="group flex flex-col overflow-hidden rounded-md border border-line bg-paper-raised transition-shadow hover:shadow-[0_2px_14px_rgba(0,0,0,0.06)]"
    >
      <div className="relative">
        <ProductPhoto brand={product.brand} className="aspect-square w-full text-3xl" />
        <div className="absolute right-2 top-2 rounded-full bg-paper-raised/90 backdrop-blur-sm">
          <FavoriteButton dsldId={product.dsld_id} size="sm" />
        </div>
        {product.off_market && (
          <span className="absolute left-2 top-2 rounded bg-paper-raised/90 px-1.5 py-0.5 font-mono text-[0.62rem] uppercase tracking-wide text-ink-soft backdrop-blur-sm">
            Off market
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-3.5">
        <span className="font-mono text-[0.68rem] uppercase tracking-wide text-ink-soft">
          {product.brand} · {CATEGORY_LABELS[product.category]}
        </span>
        <h3 className="font-serif text-[0.98rem] font-semibold leading-snug text-ink group-hover:text-accent">
          {product.name}
        </h3>
        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          {pct != null ? (
            <span className="font-mono text-[0.78rem] tabular-nums text-ink-soft">{pct}% protein</span>
          ) : (
            <span />
          )}
          <TrustBadge trust={product.trust} size="sm" />
        </div>
      </div>
    </Link>
  )
}
