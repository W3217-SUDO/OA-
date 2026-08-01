import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const apiProxyTarget = loadEnv(mode, '.', '').VITE_API_PROXY_TARGET ?? 'http://localhost:8000'
  return {
    plugins:[react()],
    server:{proxy:{'/api':apiProxyTarget}},
    build:{chunkSizeWarningLimit:1100},
  }
})
