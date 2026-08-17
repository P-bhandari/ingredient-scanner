import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

// HashRouter, not BrowserRouter: this app also ships as a single static
// HTML file (see scripts/build_artifact step) with no server to rewrite
// /product/:id back to index.html, so routing has to live in the fragment.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
)
