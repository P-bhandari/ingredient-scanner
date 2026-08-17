import type { Dataset } from './types'
import raw from './products.json'

// Bundled at build time (see webapp/scripts/prepare_data.py) rather than
// fetched at runtime -- keeps the app fully self-contained, which matters
// for both local dev and the single-file artifact build.
const dataset = raw as unknown as Dataset

export function useDataset(): { dataset: Dataset; loading: false; error: null } {
  return { dataset, loading: false, error: null }
}
