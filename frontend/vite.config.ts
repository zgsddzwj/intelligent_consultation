import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    // 仅在 ANALYZE=true 时启用包体积分析
    mode === 'analyze' && visualizer({
      open: true,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 启用源码映射（生产环境可关闭以提升构建速度）
    sourcemap: mode !== 'production',
    // 代码分割策略
    rollupOptions: {
      output: {
        // 手动分块策略：将大型第三方库拆分为独立 chunk
        manualChunks(id) {
          // React 生态核心库
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom') || id.includes('node_modules/react-router-dom')) {
            return 'react-core'
          }
          // Ant Design 组件库体积较大，单独拆分
          if (id.includes('node_modules/antd') || id.includes('node_modules/@ant-design')) {
            return 'antd'
          }
          // 数据可视化相关
          if (id.includes('node_modules/react-force-graph')) {
            return 'graph-viz'
          }
          // 其他 node_modules 按通用 vendor 打包
          if (id.includes('node_modules')) {
            return 'vendor'
          }
        },
        // 静态资源命名规则，便于缓存
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name || ''
          if (/\.(css)$/i.test(info)) {
            return 'assets/css/[name]-[hash][extname]'
          }
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(info)) {
            return 'assets/images/[name]-[hash][extname]'
          }
          if (/\.(woff2?|eot|ttf|otf)$/i.test(info)) {
            return 'assets/fonts/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        },
      },
    },
    // 压缩配置
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,      // 移除所有 console
        drop_debugger: true,     // 移除 debugger
        pure_funcs: ['console.log', 'console.info'], // 移除指定函数调用
      },
      format: {
        comments: false,         // 移除注释
      },
    },
    // 小于此阈值的资源将内联为 base64
    assetsInlineLimit: 4096,
    // 触发警告的 chunk 大小（KB）
    chunkSizeWarningLimit: 500,
  },
  // 路径别名，简化模块导入
  resolve: {
    alias: {
      '@': '/src',
      '@components': '/src/components',
      '@services': '/src/services',
      '@stores': '/src/stores',
      '@types': '/src/types',
      '@utils': '/src/utils',
    },
  },
  // 优化依赖预构建，加快冷启动
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'antd',
      '@tanstack/react-query',
      'axios',
      'zustand',
    ],
  },
}))
