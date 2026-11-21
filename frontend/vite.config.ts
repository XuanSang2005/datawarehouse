import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Read .env from the repo ROOT (shared with backend/ETL).
// Every request to /api/* is proxied to the backend -> the frontend needs no backend URL and hits no CORS errors.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', '')
  const backendPort = env.BACKEND_PORT || '8000'

  return {
    plugins: [react(), tailwindcss()],
    envDir: '..',
    server: {
      port: Number(env.FRONTEND_PORT || 5173),
      proxy: {
        '/api': `http://localhost:${backendPort}`,
      },
    },
  }
})
