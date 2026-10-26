import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'

// In development the FastAPI backend runs on :4000 and Vite proxies /api to it.
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:4000', changeOrigin: true } },
  },
  test: {
    environment: 'node',
  },
})
