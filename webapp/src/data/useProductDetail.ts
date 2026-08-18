import { useEffect, useState } from 'react'
import type { Product } from './types'

const NUM_SHARDS = 360

function shardFor(dsldId: number): number {
  return dsldId % NUM_SHARDS
}

// One cache entry per shard (~1-2MB each), not per product — visiting a
// second product from an already-fetched shard is instant and costs no
// network request. A shard is fetched at most once per session.
const shardCache = new Map<number, Promise<Product[]>>()

function loadShard(shard: number): Promise<Product[]> {
  let promise = shardCache.get(shard)
  if (!promise) {
    const base = import.meta.env.BASE_URL
    promise = fetch(`${base}data/shards/${shard}.json`).then((res) => {
      if (!res.ok) throw new Error(`shard ${shard}: ${res.status} ${res.statusText}`)
      return res.json() as Promise<Product[]>
    })
    shardCache.set(shard, promise)
  }
  return promise
}

interface ProductDetailState {
  product: Product | null
  loading: boolean
  error: string | null
}

/**
 * Fetches only the shard containing `dsldId`, not the full catalogue — the
 * detail page is the one place in the app that needs a product's full
 * ingredient list, trust certification scopes, and macro panel, and at
 * ~117,800 products that detail cannot be bundled or preloaded.
 */
export function useProductDetail(dsldId: number | null): ProductDetailState {
  const [state, setState] = useState<ProductDetailState>({
    product: null,
    loading: dsldId != null,
    error: null,
  })

  useEffect(() => {
    if (dsldId == null) {
      setState({ product: null, loading: false, error: null })
      return
    }

    let cancelled = false
    setState({ product: null, loading: true, error: null })

    loadShard(shardFor(dsldId))
      .then((products) => {
        if (cancelled) return
        const product = products.find((p) => p.dsld_id === dsldId) ?? null
        setState({ product, loading: false, error: null })
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ product: null, loading: false, error: err.message })
      })

    return () => {
      cancelled = true
    }
  }, [dsldId])

  return state
}
