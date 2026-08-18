import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { useCatalogue } from './data/useCatalogue'
import { BrowsePage } from './pages/BrowsePage'
import { ProductDetailPage } from './pages/ProductDetailPage'

/**
 * Without this, opening a product from a scrolled grid lands you partway down
 * the product page — the browser keeps the previous offset because the route
 * change never unmounts the document.
 */
function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

/**
 * The browse index is ~117,800 rows (~7.6 MB gzipped) -- fetched once here,
 * before anything that depends on it (Header's category counts, the browse
 * grid, the footer's product count) renders, rather than scattering loading
 * checks through every component that touches the catalogue.
 */
function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper">
      <div className="text-center">
        <p className="font-serif text-lg text-ink">Loading the full catalogue…</p>
        <p className="mt-1 font-mono text-[0.76rem] text-ink-soft">First visit only — cached for the session</p>
      </div>
    </div>
  )
}

function ErrorScreen({ message }: { message: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-6">
      <div className="max-w-md text-center">
        <p className="font-serif text-lg text-ink">Couldn't load the catalogue.</p>
        <p className="mt-2 text-[0.86rem] text-ink-soft">{message}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-4 rounded bg-accent px-4 py-2 font-mono text-[0.78rem] uppercase tracking-wide text-paper-raised hover:opacity-90"
        >
          Retry
        </button>
      </div>
    </div>
  )
}

export default function App() {
  const { loading, error } = useCatalogue()

  if (loading) return <LoadingScreen />
  if (error) return <ErrorScreen message={error} />

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-accent focus:px-3 focus:py-2 focus:text-paper-raised"
      >
        Skip to content
      </a>
      <ScrollToTop />
      <Header />
      <main id="main" className="flex-1">
        <Routes>
          <Route path="/" element={<BrowsePage />} />
          <Route path="/product/:id" element={<ProductDetailPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
