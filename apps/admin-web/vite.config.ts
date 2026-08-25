import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const apiProxyTarget = loadEnv(mode, '.', '').VITE_API_PROXY_TARGET ?? (mode === 'staging' ? 'http://127.0.0.1:8012' : 'http://localhost:8000')
  const apiProxy = {'/api': apiProxyTarget}
  return {
    plugins:[react()],
    server:{proxy:apiProxy},
    preview:{proxy:apiProxy},
    build:{
      chunkSizeWarningLimit:1100,
      rollupOptions:{
        output:{
          manualChunks(id) {
            if (id.indexOf('/node_modules/dingtalk-jsapi/') >= 0) return 'dingtalk-vendor'
            if (id.indexOf('/node_modules/antd/') >= 0 || id.indexOf('/node_modules/@ant-design/') >= 0) return 'antd-vendor'
            if (id.indexOf('/node_modules/react/') >= 0 || id.indexOf('/node_modules/react-dom/') >= 0 || id.indexOf('/node_modules/scheduler/') >= 0) return 'react-vendor'
          },
        },
      },
    },
  }
})
