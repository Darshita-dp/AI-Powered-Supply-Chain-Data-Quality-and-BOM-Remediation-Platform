/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: Number(loadEnv(mode, process.cwd(), 'BOMG_').BOMG_DEV_PORT ?? 5173),
    strictPort: true,
    proxy: {
      '/api':
        loadEnv(mode, process.cwd(), 'BOMG_').BOMG_API_URL ?? 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
  },
}))
