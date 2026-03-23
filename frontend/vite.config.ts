import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
        ws: false // 禁用 Vite 对 WebSocket 的代理，让前端通过 useA2FWebSocket 直连后端
      }
    }
  }
})
