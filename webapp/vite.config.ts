import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  // GitHub Pages serves this as a project page at
  // p-bhandari.github.io/ingredient-scanner/, not the domain root, so built
  // asset URLs need that prefix. The dev server has no such prefix, so this
  // only applies to `vite build` -- `npm run dev` still serves from `/`.
  base: command === 'build' ? '/ingredient-scanner/' : '/',
}))
