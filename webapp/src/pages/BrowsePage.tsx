import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ProductCard } from '../components/ProductCard'
import { FilterBar } from '../components/FilterBar'
import { allIngredients } from '../data/derived'
import { CATEGORY_LABELS, type ProteinCategory } from '../data/types'
import { useDataset } from '../data/useDataset'
import { useFavorites } from '../favorites/useFavorites'
import { matchesFilters, matchesSearch } from '../filters/apply'
import { applyFiltersToParams, filtersFromParams } from '../filters/types'

export function BrowsePage() {
  const { dataset, loading, error } = useDataset()
  const [searchParams, setSearchParams] = useSearchParams()
  const { favoriteIds } = useFavorites()

  const category = searchParams.get('category') as ProteinCategory | null
  const query = searchParams.get('q') ?? ''
  const favoritesOnly = searchParams.get('favorites') === '1'
  const filters = useMemo(() => filtersFromParams(searchParams), [searchParams])

  const { ingredientOptions, brandOptions } = useMemo(() => {
    if (!dataset) return { ingredientOptions: [], brandOptions: [] }
    const ingredients = new Set<string>()
    const brands = new Set<string>()
    for (const p of dataset.products) {
      brands.add(p.brand)
      for (const i of allIngredients(p)) ingredients.add(i.name)
    }
    return {
      ingredientOptions: [...ingredients].sort((a, b) => a.localeCompare(b)),
      brandOptions: [...brands].sort((a, b) => a.localeCompare(b)),
    }
  }, [dataset])

  const results = useMemo(() => {
    if (!dataset) return []
    return dataset.products.filter((p) => {
      if (category && p.category !== category) return false
      if (favoritesOnly && !favoriteIds.has(p.dsld_id)) return false
      if (!matchesSearch(p, query)) return false
      return matchesFilters(p, filters)
    })
  }, [dataset, category, favoritesOnly, favoriteIds, query, filters])

  if (loading) {
    return <div className="mx-auto max-w-6xl px-6 py-16 text-ink-soft">Loading dataset…</div>
  }
  if (error || !dataset) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-16 text-claim">
        Couldn't load the dataset{error ? `: ${error}` : ''}.
      </div>
    )
  }

  const heading = favoritesOnly ? 'Your favorites' : category ? CATEGORY_LABELS[category] : 'All products'

  return (
    <div className="mx-auto max-w-6xl gap-8 px-6 py-8 sm:flex sm:items-start">
      <FilterBar
        filters={filters}
        onChange={(next) => setSearchParams(applyFiltersToParams(next, searchParams))}
        ingredientOptions={ingredientOptions}
        brandOptions={brandOptions}
      />

      <div className="min-w-0 flex-1">
        <div className="mb-5 flex items-baseline justify-between gap-4">
          <h1 className="font-serif text-2xl font-semibold text-ink">{heading}</h1>
          <span className="font-mono text-[0.78rem] tabular-nums text-ink-soft">
            {results.length} product{results.length === 1 ? '' : 's'}
          </span>
        </div>

        {query && (
          <p className="mb-4 text-[0.86rem] text-ink-soft">
            Searching “{query}”
          </p>
        )}

        {results.length === 0 ? (
          <p className="rounded border border-line bg-paper-raised px-4 py-8 text-center text-ink-soft">
            No products match these filters.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {results.map((p) => (
              <ProductCard key={p.dsld_id} product={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
