import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useCatalogue } from '../data/useCatalogue'
import { CATEGORY_LABELS, CATEGORY_ORDER, type ProductCategory } from '../data/types'
import { useFavorites } from '../favorites/useFavorites'

export function Header() {
  const { catalogue } = useCatalogue()
  const [searchParams, setSearchParams] = useSearchParams()
  const { favoriteIds } = useFavorites()
  const activeCategory = searchParams.get('category')
  const showingFavorites = searchParams.get('favorites') === '1'
  const urlQuery = searchParams.get('q') ?? ''
  const [query, setQuery] = useState(urlQuery)

  const rows = catalogue?.rows ?? []

  // Sets expectations before the click, and shows the shape of the catalogue
  // for free — "Vitamins (6,759)" tells a visitor something "Vitamins" alone
  // doesn't. Categories with zero products (should only ever be the
  // "uncategorized" safety-net bucket) are omitted rather than shown empty.
  const categoryCounts = useMemo(() => {
    const counts: Partial<Record<ProductCategory, number>> = {}
    for (const row of rows) counts[row.category] = (counts[row.category] ?? 0) + 1
    return counts
  }, [rows])
  const visibleCategories = CATEGORY_ORDER.filter((c) => (categoryCounts[c] ?? 0) > 0)

  // Keeps the input in sync when `q` changes from outside this component —
  // clearing it via the chip on the results page, or a link that resets to "/".
  useEffect(() => {
    setQuery((current) => (current === urlQuery ? current : urlQuery))
  }, [urlQuery])

  // Live, not submit-on-Enter: filtering is fast enough that requiring a
  // keypress just adds friction. Reads the latest params via the functional
  // updater so a search doesn't clobber a category or filter selection made
  // moments earlier.
  function updateQuery(value: string) {
    setQuery(value)
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (value.trim()) next.set('q', value.trim())
        else next.delete('q')
        next.delete('p') // a new search invalidates whatever page you were on
        return next
      },
      { replace: true },
    )
  }

  return (
    <header className="border-b border-line-strong bg-paper-raised">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
        <Link to="/" className="flex flex-col leading-none">
          <span className="font-mono text-[0.68rem] uppercase tracking-[0.14em] text-accent">
            Ingredient &amp; certification transparency
          </span>
          <span className="font-serif text-xl font-semibold text-ink">Label Lens</span>
        </Link>

        <form onSubmit={(e) => e.preventDefault()} className="order-last w-full sm:order-none sm:w-64">
          <div className="relative">
            <input
              type="search"
              value={query}
              onChange={(e) => updateQuery(e.target.value)}
              placeholder="Search brand or product…"
              className="w-full rounded border border-line-strong bg-paper px-3 py-1.5 text-sm text-ink placeholder:text-ink-soft focus:border-accent focus:outline-none"
            />
            {query && (
              <button
                type="button"
                onClick={() => updateQuery('')}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-soft hover:text-ink"
              >
                ×
              </button>
            )}
          </div>
        </form>

        <Link
          to="/?favorites=1"
          className={`font-mono text-[0.76rem] uppercase tracking-wide transition-colors ${
            showingFavorites ? 'text-accent' : 'text-ink-soft hover:text-ink'
          }`}
        >
          Favorites {favoriteIds.size > 0 && `(${favoriteIds.size})`}
        </Link>
      </div>

      <nav className="mx-auto flex max-w-6xl flex-wrap gap-1 px-6 pb-3">
        <Link
          to="/"
          className={`rounded px-3 py-1.5 font-mono text-[0.76rem] uppercase tracking-wide transition-colors ${
            !activeCategory && !showingFavorites
              ? 'bg-accent-soft text-accent'
              : 'text-ink-soft hover:bg-code-bg hover:text-ink'
          }`}
        >
          All <span className="opacity-70">({rows.length.toLocaleString()})</span>
        </Link>
        {visibleCategories.map((cat) => (
          <Link
            key={cat}
            to={`/?category=${cat}`}
            className={`rounded px-3 py-1.5 font-mono text-[0.76rem] uppercase tracking-wide transition-colors ${
              activeCategory === cat
                ? 'bg-accent-soft text-accent'
                : 'text-ink-soft hover:bg-code-bg hover:text-ink'
            }`}
          >
            {CATEGORY_LABELS[cat]} <span className="opacity-70">({(categoryCounts[cat] ?? 0).toLocaleString()})</span>
          </Link>
        ))}
      </nav>
    </header>
  )
}
