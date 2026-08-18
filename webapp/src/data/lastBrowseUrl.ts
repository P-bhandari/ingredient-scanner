const KEY = 'll:lastBrowseUrl'

/**
 * Where "Back to browse" on the product detail page returns to.
 *
 * A plain `<Link to="/">` used to discard whatever search, filter, category,
 * shortcut and page a visitor had active — landing on "334065" from page 3
 * of a filtered search sent them back to an unfiltered page 1. `navigate(-1)`
 * isn't a fix either: it depends on exactly how they arrived (a shared link,
 * a second tab, hopping between two product pages), which isn't something
 * this component can know. Recording the last real browse URL and reading it
 * back is deterministic regardless of how the product page was reached.
 */
export function saveLastBrowseUrl(pathname: string, search: string): void {
  sessionStorage.setItem(KEY, pathname + search)
}

export function getLastBrowseUrl(): string {
  return sessionStorage.getItem(KEY) ?? '/'
}
