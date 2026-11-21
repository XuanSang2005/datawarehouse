import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Đọc .env ở THƯ MỤC GỐC repo (dùng chung với backend/ETL).
// Mọi request tới /api/* được proxy sang backend -> frontend không cần biết URL backend, không lỗi CORS.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', '')
  const backendPort = env.BACKEND_PORT || '8000'

  return {
    plugins: [react()],
    envDir: '..',
    server: {
      port: Number(env.FRONTEND_PORT || 5173),
      proxy: {
        '/api': `http://localhost:${backendPort}`,
      },
    },
  }
})
