import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react({
    // Include .js files in JSX processing
    include: "**/*.{js,jsx}",
  })],
  server: {
    port: 3000,
    proxy: {
      // '/api': {
      //   target: 'http://localhost',  // Nginx gateway
      //   changeOrigin: true,
      // },
      // '/ws': {
      //   target: 'ws://localhost',
      //   ws: true,
      //   changeOrigin: true,
      // }
      // Auth + Users → User Service
      '/api/auth':  { target: 'http://localhost:8001', changeOrigin: true },
      '/api/users': { target: 'http://localhost:8001', changeOrigin: true },

      // Tasks + Categories → Task Service
      '/api/tasks':      { target: 'http://localhost:8002', changeOrigin: true },
      '/api/categories': { target: 'http://localhost:8002', changeOrigin: true },

      // Notifications + Devices + Preferences + WebSocket → Notification Service
      '/api/notifications': { target: 'http://localhost:8003', changeOrigin: true },
      '/api/devices':       { target: 'http://localhost:8003', changeOrigin: true },
      '/api/preferences':   { target: 'http://localhost:8003', changeOrigin: true },
      '/api/ws': {
        target:      'ws://localhost:8003',
            ws:          true,
            changeOrigin: true,
      },

      // Analytics → Analytics Service
      '/api/analytics': { target: 'http://localhost:8004', changeOrigin: true },

      }
  }
})
