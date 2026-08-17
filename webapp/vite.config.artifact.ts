import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

// Separate build target: inlines everything (JS, CSS, the bundled dataset)
// into one index.html for sharing as a standalone snapshot (e.g. a Claude
// Artifact) with no server, no separate asset requests.
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile()],
  build: {
    outDir: 'dist-artifact',
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
  },
})
