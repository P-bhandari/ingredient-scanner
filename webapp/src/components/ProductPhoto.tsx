/**
 * The dataset has no product photography (DSLD doesn't carry it, and
 * sourcing real photos per-brand is a separate content task -- see PRD §5.7 /
 * §9). This renders a clean placeholder so cards and the detail page don't
 * look broken while that's unresolved: initials on a tinted ground, not a
 * broken-image icon.
 */
export function ProductPhoto({ brand, className }: { brand: string; className?: string }) {
  const initials = brand
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('')

  return (
    <div
      className={`flex items-center justify-center bg-accent-soft font-serif text-accent ${className ?? ''}`}
      aria-hidden
    >
      <span className="opacity-70">{initials || '?'}</span>
    </div>
  )
}
