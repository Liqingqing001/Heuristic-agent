import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/node_modules/@lezer/')) return 'editor-parser'
          if (
            id.includes('/node_modules/@codemirror/') ||
            id.includes('/node_modules/codemirror/')
          )
            return 'editor-core'
        },
      },
    },
  },
  server: {
    port: 5173,
    // 编辑器/工具写入临时文件时不要让 watcher 崩溃（Windows 上会 EBUSY）
    watch: {
      ignored: [
        '**/.git/**',
        '**/node_modules/**',
        '**/*.tmp',
        '**/.*.tmpdir/**',
      ],
    },
    // 开发时把 /api 代理到 FastAPI 后端，避免跨域
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
