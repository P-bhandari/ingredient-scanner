import { useFavorites } from '../favorites/useFavorites'

export function FavoriteButton({ dsldId, size = 'md' }: { dsldId: number; size?: 'sm' | 'md' }) {
  const { isFavorite, toggle } = useFavorites()
  const active = isFavorite(dsldId)
  const dim = size === 'sm' ? 16 : 20

  return (
    <button
      type="button"
      aria-pressed={active}
      aria-label={active ? 'Remove from favorites' : 'Add to favorites'}
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        toggle(dsldId)
      }}
      className="inline-flex items-center justify-center rounded-full p-1.5 text-ink-soft transition-colors hover:bg-code-bg hover:text-accent"
    >
      <svg
        width={dim}
        height={dim}
        viewBox="0 0 24 24"
        fill={active ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth={1.6}
        className={active ? 'text-accent' : ''}
      >
        <path d="M12 20.5s-7.6-4.6-10-9C.5 8 1.6 4.5 5 3.6c2-.5 4 .3 5 2 1-1.7 3-2.5 5-2C18.4 4.5 19.5 8 17 11.5c-2.4 4.4-5 9-5 9Z" />
      </svg>
    </button>
  )
}
