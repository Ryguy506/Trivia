/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Same-origin API: the page and the backend share one address, so it works over the LAN with no CORS change
  server: {
    proxy: {
      '/rooms': 'http://localhost:8000',
      '/categories': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  // globals lets Testing Library clean up the DOM after each test on its own
  test: { environment: 'jsdom', globals: true },
})
