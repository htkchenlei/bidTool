import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      '/process-excel': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      '/file-parse': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      '/regions': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})