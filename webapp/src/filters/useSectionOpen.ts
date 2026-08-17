import { useState } from 'react'

/**
 * Persisted open/closed state for a collapsible filter section. Backed by
 * localStorage rather than component state so a section a user closes stays
 * closed across visits — the whole point of making it collapsible in the
 * first place is to let people hide facets they never touch.
 */
export function useSectionOpen(key: string, defaultOpen: boolean): [boolean, () => void] {
  const storageKey = `labellens:filterSection:${key}`

  const [open, setOpen] = useState(() => {
    try {
      const stored = localStorage.getItem(storageKey)
      return stored === null ? defaultOpen : stored === '1'
    } catch {
      return defaultOpen
    }
  })

  function toggle() {
    setOpen((prev) => {
      const next = !prev
      try {
        localStorage.setItem(storageKey, next ? '1' : '0')
      } catch {
        // localStorage unavailable (private browsing, etc.) — state still
        // works for this session via the component state above.
      }
      return next
    })
  }

  return [open, toggle]
}
