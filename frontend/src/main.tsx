/**
 * 智能医疗管家平台 - 应用入口
 * 
 * 技术栈：
 * - React 18 + TypeScript
 * - Vite (构建工具)
 * - Ant Design 5 (UI组件库)
 * - @tanstack/react-query (数据请求)
 * - Zustand (状态管理)
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './index.css'

// 创建 React Query 客户端实例
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 数据过期时间：5分钟
      staleTime: 5 * 60 * 1000,
      // 缓存时间：10分钟
      gcTime: 10 * 60 * 1000,
      // 失败重试次数
      retry: 2,
      // 重试延迟
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // 窗口聚焦时是否重新请求
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
})

// Ant Design 全局主题配置
const themeConfig = {
  token: {
    // 主色调
    colorPrimary: '#667eea',
    
    // 圆角
    borderRadius: 8,
    
    // 字体
    fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 
      'Hiragino Sans GB', 'Microsoft YaHei', sans-serif`,
    
    // 阴影
    boxShadow: '0 4px 16px rgba(102, 126, 234, 0.15)',
    
    // 动画
    motionDurationMid: '0.3s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
  components: {
    Button: {
      primaryShadow: '0 4px 16px rgba(102, 126, 234, 0.3)',
      controlHeight: 44,
    },
    Input: {
      controlHeight: 48,
      paddingInline: 16,
    },
    Card: {
      borderRadiusLG: 16,
      boxShadowTertiary: '0 4px 20px rgba(0, 0, 0, 0.08)',
    },
    Message: {
      contentBg: '#ffffff',
    },
  },
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN} theme={themeConfig}>
        <AntdApp>
          <App />
        </AntdApp>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)

// 开发环境下的性能监控
if (import.meta.env.DEV) {
  console.log(
    '%c🏥 智能医疗管家平台 %cv0.1.0',
    'color: #667eea; font-size: 18px; font-weight: bold;',
    'color: #999; font-size: 12px;'
  )
  console.log(
    '%c⚠️ 开发模式 - 请勿在生产环境使用此控制台',
    'color: #faad14; font-size: 12px;'
  )
}

