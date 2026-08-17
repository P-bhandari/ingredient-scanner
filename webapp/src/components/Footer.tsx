import { useDataset } from '../data/useDataset'

/**
 * A trust product that never says how fresh its own data is undercuts
 * itself. dataset.generated already exists on every export; it just wasn't
 * shown anywhere.
 */
export function Footer() {
  const { dataset } = useDataset()

  let formatted: string | null = null
  try {
    formatted = new Date(dataset.generated).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    formatted = null
  }

  return (
    <footer className="border-t border-line bg-paper-raised">
      <div className="mx-auto max-w-6xl px-6 py-6 font-mono text-[0.72rem] leading-relaxed text-ink-soft">
        <p>
          {formatted ? `Data as of ${formatted}` : 'Data freshness unavailable'} · {dataset.products.length}{' '}
          products
        </p>
        <p className="mt-1">{dataset.source_citation}</p>
        <p className="mt-1">Licence: {dataset.licence}</p>
      </div>
    </footer>
  )
}
