import { useEffect } from 'react'

/**
 * Every route was titled "Label Lens", which makes tabs, history and
 * bookmarks indistinguishable and gives screen readers nothing to announce on
 * navigation.
 */
export function useDocumentTitle(title: string | null) {
  useEffect(() => {
    document.title = title ? `${title} · Label Lens` : 'Label Lens'
    return () => {
      document.title = 'Label Lens'
    }
  }, [title])
}
