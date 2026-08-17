import { useEffect, useState } from 'react'
import { activeCount, type Filters } from '../filters/types'
import { FilterBar, type FacetCounts } from './FilterBar'

/**
 * Tracks a media query via matchMedia rather than a CSS breakpoint, because
 * this component renders one FilterBar instance and switches its chrome
 * (sticky sidebar vs. drawer) rather than rendering two copies — two copies
 * would duplicate every form control's identity (and with it, autocomplete
 * datalist ids) in the DOM at once.
 */
function useIsDesktop(breakpointPx = 640): boolean {
  const query = `(min-width: ${breakpointPx}px)`
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : true,
  )
  useEffect(() => {
    const mql = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [query])
  return isDesktop
}

interface FilterPanelProps {
  filters: Filters
  onChange: (next: Filters) => void
  ingredientOptions: string[]
  brandOptions: string[]
  counts: FacetCounts
  resultCount: number
}

export function FilterPanel(props: FilterPanelProps) {
  const isDesktop = useIsDesktop()
  const [open, setOpen] = useState(false)
  const active = activeCount(props.filters)

  // A resize past the breakpoint while the drawer is open would otherwise
  // leave a phantom overlay mounted behind the now-visible sidebar.
  useEffect(() => {
    if (isDesktop) setOpen(false)
  }, [isDesktop])

  // The drawer is a focus trap of one: Escape closes it, matching every
  // other dismissible overlay a keyboard user has met before.
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  if (isDesktop) {
    return (
      <aside className="w-full shrink-0 sm:sticky sm:top-4 sm:max-h-[calc(100vh-2rem)] sm:w-64 sm:self-start sm:overflow-y-auto">
        <FilterBar {...props} />
      </aside>
    )
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        className="mb-4 flex w-full items-center justify-center gap-2 rounded border border-line-strong bg-paper-raised px-4 py-2.5 font-mono text-[0.8rem] uppercase tracking-wide text-ink"
      >
        Filters
        {active > 0 && (
          <span className="rounded-full bg-accent px-1.5 py-0.5 text-[0.68rem] text-paper-raised">{active}</span>
        )}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end" role="dialog" aria-modal="true" aria-label="Filters">
          <button
            type="button"
            aria-label="Close filters"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/40"
          />
          <div className="relative z-10 flex max-h-[85vh] flex-col rounded-t-xl border-t border-line-strong bg-paper shadow-[0_-4px_24px_rgba(0,0,0,0.15)]">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <span className="font-serif text-lg font-semibold text-ink">Filters</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close filters"
                className="rounded p-1 text-ink-soft hover:text-ink"
              >
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
                  <path d="M4 4l10 10M14 4 4 14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-1">
              <FilterBar {...props} />
            </div>
            <div className="border-t border-line p-4">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="w-full rounded bg-accent py-2.5 font-mono text-[0.82rem] uppercase tracking-wide text-paper-raised hover:opacity-90"
              >
                Show {props.resultCount} product{props.resultCount === 1 ? '' : 's'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
