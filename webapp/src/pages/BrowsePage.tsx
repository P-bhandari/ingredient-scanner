import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ProductCard } from '../components/ProductCard'
import { FilterPanel } from '../components/FilterPanel'
import type { FacetCounts } from '../components/FilterBar'
import { allIngredients } from '../data/derived'
import { CATEGORY_LABELS, type ProteinCategory } from '../data/types'
import { useDataset } from '../data/useDataset'
import { useFavorites } from '../favorites/useFavorites'
import { useDocumentTitle } from '../useDocumentTitle'
import { matchesFilters, matchesSearch, sortProducts, SORT_LABELS, type SortKey } from '../filters/apply'
import {
  activeCount,
  applyFiltersToParams,
  EMPTY_FILTERS,
  filtersFromParams,
  isEmpty,
  type Filters,
} from '../filters/types'

const SORT_KEYS = Object.keys(SORT_LABELS) as SortKey[]

export function BrowsePage() {
  const { dataset } = useDataset()
  const [searchParams, setSearchParams] = useSearchParams()
  const { favoriteIds } = useFavorites()

  const category = searchParams.get('category') as ProteinCategory | null
  const query = searchParams.get('q') ?? ''
  const favoritesOnly = searchParams.get('favorites') === '1'
  const filters = useMemo(() => filtersFromParams(searchParams), [searchParams])

  function setFilters(next: Filters) {
    setSearchParams(applyFiltersToParams(next, searchParams), { replace: true })
  }

  const { ingredientOptions, brandOptions } = useMemo(() => {
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

  /** Products passing everything except the facet being counted. */
  const scoped = useMemo(
    () =>
      dataset.products.filter((p) => {
        if (category && p.category !== category) return false
        if (favoritesOnly && !favoriteIds.has(p.dsld_id)) return false
        return matchesSearch(p, query)
      }),
    [dataset, category, favoritesOnly, favoriteIds, query],
  )

  const results = useMemo(
    () => sortProducts(scoped.filter((p) => matchesFilters(p, filters)), filters.sort),
    [scoped, filters],
  )

  /**
   * Counts are computed against everything else that's active, so a number
   * always answers "how many would I get if I clicked this" rather than a
   * static catalogue total. Zero-count options are then disabled, which is
   * what makes AND-matching usable instead of a dead end.
   */
  const counts: FacetCounts = useMemo(() => {
    const countWith = (patch: Partial<Filters>) =>
      scoped.filter((p) => matchesFilters(p, { ...filters, ...patch })).length

    const certifiers: Record<string, number> = {}
    for (const c of [
      'nsf_certified_for_sport',
      'nsf_contents_certified',
      'informed_sport',
      'informed_choice',
      'usp_verified',
      'bscg',
    ] as const) {
      certifiers[c] = filters.certifiers.includes(c)
        ? countWith({})
        : countWith({ certifiers: [...filters.certifiers, c] })
    }

    const allergens: Record<string, number> = {}
    for (const a of ['milk', 'soy', 'egg', 'wheat', 'peanut', 'tree nut', 'fish', 'shellfish', 'sesame', 'gluten']) {
      allergens[a] = filters.excludeAllergens.includes(a)
        ? countWith({})
        : countWith({ excludeAllergens: [...filters.excludeAllergens, a] })
    }

    return {
      certifiers,
      allergens,
      flags: {
        noCert: countWith({ noCertOnly: true }),
        noArtificialSweetener: countWith({ noArtificialSweetener: true }),
        noProprietaryBlend: countWith({ noProprietaryBlend: true }),
        onMarketOnly: countWith({ onMarketOnly: true }),
      },
    }
  }, [scoped, filters])

  const heading = favoritesOnly ? 'Your favorites' : category ? CATEGORY_LABELS[category] : 'All products'
  const active = activeCount(filters)
  useDocumentTitle(query ? `${query} — search` : heading)

  return (
    <div className="mx-auto max-w-6xl gap-8 px-6 py-8 sm:flex sm:items-start">
      <FilterPanel
        filters={filters}
        onChange={setFilters}
        ingredientOptions={ingredientOptions}
        brandOptions={brandOptions}
        counts={counts}
        resultCount={results.length}
      />

      <div className="min-w-0 flex-1">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
          <h1 className="font-serif text-2xl font-semibold text-ink">{heading}</h1>
          <div className="flex items-center gap-3">
            <span className="font-mono text-[0.78rem] tabular-nums text-ink-soft">
              {results.length} of {scoped.length}
            </span>
            <label className="flex items-center gap-1.5">
              <span className="sr-only">Sort by</span>
              <select
                value={filters.sort}
                onChange={(e) => setFilters({ ...filters, sort: e.target.value as SortKey })}
                className="rounded border border-line-strong bg-paper px-2 py-1 font-mono text-[0.74rem] text-ink focus:border-accent focus:outline-none"
              >
                {SORT_KEYS.map((k) => (
                  <option key={k} value={k}>
                    {SORT_LABELS[k]}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <ActiveFilterChips
          filters={filters}
          query={query}
          onChange={setFilters}
          onClearSearch={() => {
            const next = new URLSearchParams(searchParams)
            next.delete('q')
            setSearchParams(next, { replace: true })
          }}
        />

        {results.length === 0 ? (
          <EmptyState filters={filters} scopedCount={scoped.length} onChange={setFilters} />
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {results.map((p) => (
              <ProductCard key={p.dsld_id} product={p} />
            ))}
          </div>
        )}

        {active > 0 && results.length > 0 && (
          <p className="mt-6 text-[0.78rem] text-ink-soft">
            {active} filter{active === 1 ? '' : 's'} applied.
          </p>
        )}
      </div>
    </div>
  )
}

/** Removable chips, so each filter can be undone without "Clear all". */
function ActiveFilterChips({
  filters,
  query,
  onChange,
  onClearSearch,
}: {
  filters: Filters
  query: string
  onChange: (f: Filters) => void
  onClearSearch: () => void
}) {
  const chips: Array<{ label: string; clear: () => void }> = []

  for (const v of filters.includeIngredients) {
    chips.push({
      label: `has: ${v}`,
      clear: () => onChange({ ...filters, includeIngredients: filters.includeIngredients.filter((x) => x !== v) }),
    })
  }
  for (const v of filters.excludeIngredients) {
    chips.push({
      label: `no: ${v}`,
      clear: () => onChange({ ...filters, excludeIngredients: filters.excludeIngredients.filter((x) => x !== v) }),
    })
  }
  for (const v of filters.certifiers) {
    chips.push({
      label: v.replace(/_/g, ' '),
      clear: () => onChange({ ...filters, certifiers: filters.certifiers.filter((x) => x !== v) }),
    })
  }
  for (const v of filters.brands) {
    chips.push({ label: v, clear: () => onChange({ ...filters, brands: filters.brands.filter((x) => x !== v) }) })
  }
  for (const v of filters.excludeAllergens) {
    chips.push({
      label: `no ${v}`,
      clear: () => onChange({ ...filters, excludeAllergens: filters.excludeAllergens.filter((x) => x !== v) }),
    })
  }
  if (filters.noCertOnly) chips.push({ label: 'uncertified only', clear: () => onChange({ ...filters, noCertOnly: false }) })
  if (filters.noArtificialSweetener)
    chips.push({ label: 'no artificial sweetener', clear: () => onChange({ ...filters, noArtificialSweetener: false }) })
  if (filters.noProprietaryBlend)
    chips.push({ label: 'no proprietary blend', clear: () => onChange({ ...filters, noProprietaryBlend: false }) })
  if (filters.onMarketOnly === false)
    chips.push({ label: 'including off-market', clear: () => onChange({ ...filters, onMarketOnly: true }) })
  if (filters.requireAllergenDeclaration)
    chips.push({ label: 'declared allergens only', clear: () => onChange({ ...filters, requireAllergenDeclaration: false }) })
  if (filters.minProteinPct != null)
    chips.push({ label: `≥${filters.minProteinPct}% protein`, clear: () => onChange({ ...filters, minProteinPct: null }) })

  if (!chips.length && !query) return null

  return (
    <div className="mb-4 flex flex-wrap items-center gap-1.5">
      {query && (
        <button
          type="button"
          onClick={onClearSearch}
          className="inline-flex items-center gap-1 rounded-[3px] border border-line-strong bg-code-bg px-2 py-1 font-mono text-[0.7rem] text-ink-soft hover:border-accent hover:text-accent"
        >
          search: “{query}”
          <span aria-hidden>×</span>
          <span className="sr-only">Clear search</span>
        </button>
      )}
      {chips.map((c) => (
        <button
          key={c.label}
          type="button"
          onClick={c.clear}
          className="inline-flex items-center gap-1 rounded-[3px] border border-line-strong bg-accent-soft px-2 py-1 font-mono text-[0.7rem] text-accent hover:border-accent"
        >
          {c.label}
          <span aria-hidden>×</span>
          <span className="sr-only">Remove filter</span>
        </button>
      ))}
    </div>
  )
}

/**
 * A dead end is a design failure. Name the filter most likely responsible and
 * offer to drop just that one before suggesting a full reset.
 */
function EmptyState({
  filters,
  scopedCount,
  onChange,
}: {
  filters: Filters
  scopedCount: number
  onChange: (f: Filters) => void
}) {
  const suspects: Array<{ label: string; relax: () => void }> = []

  if (filters.certifiers.length > 1 && filters.certMatchMode === 'all') {
    suspects.push({
      label: `Match any of your ${filters.certifiers.length} certifications instead of all`,
      relax: () => onChange({ ...filters, certMatchMode: 'any' }),
    })
  }
  if (filters.certifiers.length) {
    suspects.push({ label: 'Remove the certification filter', relax: () => onChange({ ...filters, certifiers: [] }) })
  }
  if (filters.excludeAllergens.length) {
    suspects.push({
      label: 'Remove the allergen exclusions',
      relax: () => onChange({ ...filters, excludeAllergens: [], requireAllergenDeclaration: false }),
    })
  }
  if (filters.includeIngredients.length > 1 && filters.ingredientMatchMode === 'all') {
    suspects.push({
      label: 'Match any of your ingredients instead of all',
      relax: () => onChange({ ...filters, ingredientMatchMode: 'any' }),
    })
  }
  if (filters.minProteinPct != null) {
    suspects.push({
      label: `Drop the ≥${filters.minProteinPct}% protein minimum`,
      relax: () => onChange({ ...filters, minProteinPct: null }),
    })
  }

  return (
    <div className="rounded border border-line bg-paper-raised px-5 py-8 text-center">
      <p className="font-serif text-lg text-ink">No products match these filters.</p>
      <p className="mt-1 text-[0.86rem] text-ink-soft">
        {scopedCount} product{scopedCount === 1 ? '' : 's'} available before filtering.
      </p>
      {suspects.length > 0 && (
        <ul className="mx-auto mt-4 flex max-w-sm flex-col gap-2">
          {suspects.slice(0, 3).map((s) => (
            <li key={s.label}>
              <button
                type="button"
                onClick={s.relax}
                className="w-full rounded border border-line-strong px-3 py-1.5 text-[0.82rem] text-accent hover:border-accent"
              >
                {s.label}
              </button>
            </li>
          ))}
        </ul>
      )}
      {!isEmpty(filters) && (
        <button
          type="button"
          onClick={() => onChange({ ...EMPTY_FILTERS, sort: filters.sort })}
          className="mt-4 font-mono text-[0.74rem] uppercase tracking-wide text-ink-soft hover:text-accent"
        >
          Clear all filters
        </button>
      )}
    </div>
  )
}
