import { useEffect, useState } from 'react'
import type { CatalogueMeta, Facets, IndexRow } from './types'

export interface Catalogue {
  rows: IndexRow[]
  meta: CatalogueMeta
  facets: Facets
}

interface CatalogueState {
  catalogue: Catalogue | null
  loading: boolean
  error: string | null
}

// Module-level cache: index.json is ~60MB (7.6MB gzipped) -- fetched once for
// the whole session, not once per component. Every consumer sees the same
// promise rather than racing independent fetches.
let cache: Catalogue | null = null
let inflight: Promise<Catalogue> | null = null

function load(): Promise<Catalogue> {
  if (cache) return Promise.resolve(cache)
  if (inflight) return inflight

  const base = import.meta.env.BASE_URL
  const getJson = <T,>(name: string) =>
    fetch(`${base}data/${name}`).then((res) => {
      if (!res.ok) throw new Error(`${name}: ${res.status} ${res.statusText}`)
      return res.json() as Promise<T>
    })

  inflight = Promise.all([
    getJson<IndexRow[]>('index.json'),
    getJson<CatalogueMeta>('meta.json'),
    getJson<Facets>('facets.json'),
  ]).then(([rows, meta, facets]) => {
    cache = { rows, meta, facets }
    return cache
  })

  return inflight
}

/**
 * The full ~117,800-row browse index, plus dataset metadata and precomputed
 * autocomplete facets. Fetched once at app startup (see App.tsx's loading
 * gate) and cached for the session — everything else (BrowsePage, Header's
 * category counts, Footer) reads from this same in-memory copy rather than
 * re-fetching.
 */
export function useCatalogue(): CatalogueState {
  const [state, setState] = useState<CatalogueState>({
    catalogue: cache,
    loading: !cache,
    error: null,
  })

  useEffect(() => {
    if (cache) return
    let cancelled = false

    load()
      .then((catalogue) => {
        if (!cancelled) setState({ catalogue, loading: false, error: null })
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ catalogue: null, loading: false, error: err.message })
      })

    return () => {
      cancelled = true
    }
  }, [])

  return state
}
