import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'labellens:favorites'

function readStored(): number[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as number[]) : []
  } catch {
    return []
  }
}

let listeners: Array<(ids: Set<number>) => void> = []
let state = new Set<number>(readStored())

function commit(next: Set<number>) {
  state = next
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...next]))
  listeners.forEach((l) => l(state))
}

export function useFavorites() {
  const [ids, setIds] = useState(state)

  useEffect(() => {
    listeners.push(setIds)
    return () => {
      listeners = listeners.filter((l) => l !== setIds)
    }
  }, [])

  const isFavorite = useCallback((dsldId: number) => ids.has(dsldId), [ids])

  const toggle = useCallback((dsldId: number) => {
    const next = new Set(state)
    if (next.has(dsldId)) next.delete(dsldId)
    else next.add(dsldId)
    commit(next)
  }, [])

  return { favoriteIds: ids, isFavorite, toggle }
}
