import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

const basePath = process.env.VITE_BASE_PATH ?? '/'
const basePrefix = basePath === '/' ? '' : basePath.replace(/\/$/, '')

export default defineConfig({
  base: basePath,

  plugins: [react(), tailwindcss()],

  server: {
    port: 8080,
    strictPort: true,
    proxy: {
      [`${basePrefix}/api`]: {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(new RegExp(`^${basePrefix}`), ''),
      },
    },
  },

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
