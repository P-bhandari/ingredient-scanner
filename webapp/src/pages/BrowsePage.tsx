import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ProductCard } from '../components/ProductCard'
import { FilterPanel } from '../components/FilterPanel'
import type { FacetCounts } from '../components/FilterBar'
import { CATEGORY_LABELS, type ProductCategory } from '../data/types'
import { useCatalogue } from '../data/useCatalogue'
import { useFavorites } from '../favorites/useFavorites'
import { useDocumentTitle } from '../useDocumentTitle'
import {
  allergenConstraintSatisfied,
  certifierConstraintSatisfied,
  matchesFilters,
  matchesFiltersExcept,
  matchesSearch,
  sortProducts,
  SORT_LABELS,
  type SortKey,
} from '../filters/apply'
import {
  activeCount,
  applyFiltersToParams,
  EMPTY_FILTERS,
  filtersFromParams,
  isEmpty,
  type Filters,
} from '../filters/types'

const SORT_KEYS = Object.keys(SORT_LABELS) as SortKey[]

// The catalogue is ~117,800 rows. Rendering every match as a card with no
// pagination was the actual cause of a multi-second (sometimes 30+ second)
// main-thread block on load — not the filter/facet computation, which is
// cheap by comparison. React mounting tens of thousands of card components
// at once is not something any amount of memoizing the data underneath it
// fixes; the render itself has to be bounded.
const PAGE_SIZE = 60

export function BrowsePage() {
  const { catalogue } = useCatalogue()
  const [searchParams, setSearchParams] = useSearchParams()
  const { favoriteIds } = useFavorites()

  const category = searchParams.get('category') as ProductCategory | null
  const query = searchParams.get('q') ?? ''
  const favoritesOnly = searchParams.get('favorites') === '1'
  const filters = useMemo(() => filtersFromParams(searchParams), [searchParams])
  const requestedPage = Number(searchParams.get('p') ?? '1')
  const page = Number.isFinite(requestedPage) && requestedPage >= 1 ? Math.floor(requestedPage) : 1

  // Any change to what the result set contains has to drop back to page 1 —
  // otherwise narrowing a filter can strand you on a now-nonexistent page 47.
  function setFilters(next: Filters) {
    const params = applyFiltersToParams(next, searchParams)
    params.delete('p')
    setSearchParams(params, { replace: true })
  }

  function goToPage(next: number) {
    const params = new URLSearchParams(searchParams)
    if (next <= 1) params.delete('p')
    else params.set('p', String(next))
    setSearchParams(params, { replace: true })
    window.scrollTo(0, 0)
  }

  const rows = catalogue?.rows ?? []
  // Precomputed server-side (webapp/scripts/prepare_full_catalogue.py) —
  // scanning every ingredientNames array across ~117,800 rows to build these
  // two lists client-side blocked the main thread for tens of seconds.
  const ingredientOptions = catalogue?.facets.ingredientNames ?? []
  const brandOptions = catalogue?.facets.brands ?? []

  /** Rows passing everything except the facet being counted. */
  const scoped = useMemo(() => {
    return rows.filter((row) => {
      if (category && row.category !== category) return false
      if (favoritesOnly && !favoriteIds.has(row.id)) return false
      return matchesSearch(row, query)
    })
  }, [rows, category, favoritesOnly, favoriteIds, query])

  const results = useMemo(() => {
    return sortProducts(scoped.filter((row) => matchesFilters(row, filters)), filters.sort)
  }, [scoped, filters])

  /**
   * Counts are computed against everything else that's active, so a number
   * always answers "how many would I get if I clicked this" rather than a
   * static catalogue total. Zero-count options are then disabled, which is
   * what makes AND-matching usable instead of a dead end.
   *
   * Naively, this is 20 full re-scans of `scoped` (one per certifier/allergen
   * option), each re-running every filter dimension — ingredients, brand,
   * flags — that doesn't even vary across those options. At ~117,800 rows
   * that measured at ~1.7s of blocking main-thread work. Instead: compute
   * "passes everything except certifiers" once and "...except allergens"
   * once (two full scans), then check just the one varying constraint per
   * option against those already-narrowed lists.
   */
  const counts: FacetCounts = useMemo(() => {
    const countWith = (patch: Partial<Filters>) =>
      scoped.filter((row) => matchesFilters(row, { ...filters, ...patch })).length

    const baseForCert = scoped.filter((row) => matchesFiltersExcept(row, filters, 'certifiers'))
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
        ? baseForCert.filter((row) =>
            certifierConstraintSatisfied(row, filters.certifiers, filters.certMatchMode),
          ).length
        : baseForCert.filter((row) =>
            certifierConstraintSatisfied(row, [...filters.certifiers, c], filters.certMatchMode),
          ).length
    }

    const baseForAllergen = scoped.filter((row) => matchesFiltersExcept(row, filters, 'allergens'))
    const allergens: Record<string, number> = {}
    for (const a of ['milk', 'soy', 'egg', 'wheat', 'peanut', 'tree nut', 'fish', 'shellfish', 'sesame', 'gluten']) {
      allergens[a] = filters.excludeAllergens.includes(a)
        ? baseForAllergen.filter((row) =>
            allergenConstraintSatisfied(row, filters.excludeAllergens, filters.requireAllergenDeclaration),
          ).length
        : baseForAllergen.filter((row) =>
            allergenConstraintSatisfied(row, [...filters.excludeAllergens, a], filters.requireAllergenDeclaration),
          ).length
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

  const totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pagedResults = useMemo(
    () => results.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [results, currentPage],
  )

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
              {results.length > 0
                ? `${((currentPage - 1) * PAGE_SIZE + 1).toLocaleString()}–${Math.min(currentPage * PAGE_SIZE, results.length).toLocaleString()} of ${results.length.toLocaleString()}`
                : `0 of ${scoped.length.toLocaleString()}`}
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
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {pagedResults.map((row) => (
                <ProductCard key={row.id} row={row} />
              ))}
            </div>
            {totalPages > 1 && (
              <Pagination page={currentPage} totalPages={totalPages} onChange={goToPage} />
            )}
          </>
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

function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number
  totalPages: number
  onChange: (page: number) => void
}) {
  // A handful of neighbours plus the first/last page, with gaps collapsed to
  // an ellipsis — enough to navigate 1,900+ pages without listing them all.
  const radius = 2
  const pages = new Set<number>([1, totalPages])
  for (let p = page - radius; p <= page + radius; p++) {
    if (p >= 1 && p <= totalPages) pages.add(p)
  }
  const sorted = [...pages].sort((a, b) => a - b)

  return (
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-center gap-1">
      <button
        type="button"
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="rounded border border-line-strong px-2.5 py-1.5 font-mono text-[0.76rem] text-ink-soft hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
      >
        ‹ Prev
      </button>
      {sorted.map((p, i) => (
        <span key={p} className="flex items-center gap-1">
          {i > 0 && p - sorted[i - 1] > 1 && <span className="px-1 text-ink-soft">…</span>}
          <button
            type="button"
            onClick={() => onChange(p)}
            aria-current={p === page ? 'page' : undefined}
            className={`min-w-[2rem] rounded px-2 py-1.5 font-mono text-[0.76rem] tabular-nums ${
              p === page ? 'bg-accent-soft text-accent' : 'text-ink-soft hover:text-ink'
            }`}
          >
            {p}
          </button>
        </span>
      ))}
      <button
        type="button"
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="rounded border border-line-strong px-2.5 py-1.5 font-mono text-[0.76rem] text-ink-soft hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
      >
        Next ›
      </button>
    </nav>
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
        {scopedCount.toLocaleString()} product{scopedCount === 1 ? '' : 's'} available before filtering.
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
