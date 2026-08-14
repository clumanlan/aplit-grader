/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Fixed port, not Vite's 5173 default: this machine also runs another
    // project on 5173, and the backend's CORS allow_origins is pinned to
    // match this exact port. strictPort fails loudly instead of silently
    // falling back to a port the backend won't accept requests from.
    port: 5180,
    strictPort: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
