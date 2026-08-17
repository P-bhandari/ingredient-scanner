import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { CATEGORY_LABELS, type ProteinCategory } from '../data/types'
import { useFavorites } from '../favorites/useFavorites'

const CATEGORIES: ProteinCategory[] = ['whey', 'plant', 'pea', 'casein', 'collagen']

export function Header() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { favoriteIds } = useFavorites()
  const activeCategory = searchParams.get('category')
  const showingFavorites = searchParams.get('favorites') === '1'
  const [query, setQuery] = useState(searchParams.get('q') ?? '')

  function submitSearch(e: React.FormEvent) {
    e.preventDefault()
    const next = new URLSearchParams()
    if (query.trim()) next.set('q', query.trim())
    navigate(`/?${next.toString()}`)
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

        <form onSubmit={submitSearch} className="order-last w-full sm:order-none sm:w-64">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search brand or product…"
            className="w-full rounded border border-line-strong bg-paper px-3 py-1.5 text-sm text-ink placeholder:text-ink-soft focus:border-accent focus:outline-none"
          />
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
          All
        </Link>
        {CATEGORIES.map((cat) => (
          <Link
            key={cat}
            to={`/?category=${cat}`}
            className={`rounded px-3 py-1.5 font-mono text-[0.76rem] uppercase tracking-wide transition-colors ${
              activeCategory === cat
                ? 'bg-accent-soft text-accent'
                : 'text-ink-soft hover:bg-code-bg hover:text-ink'
            }`}
          >
            {CATEGORY_LABELS[cat]}
          </Link>
        ))}
      </nav>
    </header>
  )
}
