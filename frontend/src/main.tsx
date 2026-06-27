/**
 * 智能医疗管家平台 - 应用入口
 *
 * 技术栈：
 * - React 18 + TypeScript 5
 * - Vite 5 (构建工具)
 * - Ant Design 5 (UI组件库)
 * - @tanstack/react-query 5 (数据请求/缓存)
 * - Zustand 4 (状态管理)
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider, App as AntdApp, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'
import './index.css'

// 创建 React Query 客户端实例
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
      onSettled: (_data, error) => {
        if (error) {
          console.warn('[Mutation] 操作失败:', error)
        }
      },
    },
  },
})

// 主题切换支持
const getThemeAlgorithm = () => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme === 'dark') return theme.darkAlgorithm
  if (savedTheme === 'light') return theme.defaultAlgorithm
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? theme.darkAlgorithm
    : theme.defaultAlgorithm
}

// Ant Design 全局主题配置 v3.0
const themeConfig = {
  algorithm: getThemeAlgorithm(),

  token: {
    // ===== 主色调 =====
    colorPrimary: '#2563eb',
    colorSuccess: '#16a34a',
    colorWarning: '#d97706',
    colorError: '#dc2626',
    colorInfo: '#2563eb',

    // ===== 圆角 =====
    borderRadius: 8,
    borderRadiusLG: 16,
    borderRadiusSM: 6,
    borderRadiusXS: 4,

    // ===== 字体 =====
    fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
      'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica,
      Arial, sans-serif`,
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeSM: 13,
    fontSizeXL: 20,

    // ===== 阴影 =====
    boxShadow: '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
    boxShadowSecondary: '0 4px 12px rgba(15, 23, 42, 0.08)',

    // ===== 动画 =====
    motionDurationMid: '0.25s',
    motionDurationSlow: '0.4s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    motionEaseOut: 'cubic-bezier(0, 0, 0.2, 1)',

    // ===== 间距 =====
    padding: 16,
    paddingLG: 24,
    paddingSM: 12,
    paddingXS: 8,

    // ===== 控件高度 =====
    controlHeight: 40,
    controlHeightLG: 48,
    controlHeightSM: 32,

    // ===== 线宽 =====
    lineWidth: 1,
    lineWidthBold: 2,

    wireframe: false,
  },

  components: {
    Button: {
      primaryShadow: '0 2px 8px rgba(37, 99, 235, 0.2)',
      fontWeight: 600,
      contentFontSizeLG: 16,
    },

    Input: {
      controlHeight: 44,
      paddingInline: 14,
      activeBorderColor: '#2563eb',
      hoverBorderColor: '#60a5fa',
      activeShadow: '0 0 0 3px rgba(37, 99, 235, 0.08)',
    },

    Textarea: {
      paddingInline: 14,
    },

    Card: {
      borderRadiusLG: 16,
      boxShadowTertiary: '0 1px 3px rgba(15, 23, 42, 0.06)',
      paddingLG: 24,
    },

    Message: {
      contentBg: '#ffffff',
      contentPaddingMD: '12px 20px',
    },

    Tag: {
      borderRadiusSM: 20,
    },

    Select: {
      optionSelectedBg: 'rgba(37, 99, 235, 0.06)',
    },

    Table: {
      headerBg: '#f8fafc',
      rowHoverBg: 'rgba(37, 99, 235, 0.02)',
      borderColor: '#e2e8f0',
      headerBorderRadius: 10,
    },

    Modal: {
      borderRadiusLG: 20,
    },

    Menu: {
      itemBorderRadius: 10,
      itemMarginBlock: 4,
      itemMarginInline: 8,
      iconSize: 18,
      itemActiveBg: 'rgba(37, 99, 235, 0.1)',
      itemHoverBg: 'rgba(37, 99, 235, 0.05)',
    },

    Layout: {
      headerPadding: '0 24px',
      bodyPadding: 24,
      footerPadding: '12px 24px',
    },

    List: {
      itemPadding: '12px 0',
    },

    Progress: {
      defaultColor: '#2563eb',
      remainingColor: 'rgba(15, 23, 42, 0.06)',
    },

    Badge: {
      dotSize: 8,
    },

    Avatar: {
      containerSize: 40,
      containerSizeLG: 48,
      containerSizeSM: 32,
    },

    Statistic: {
      contentFontSize: 24,
    },

    Tabs: {
      inkBarColor: '#2563eb',
      itemActiveColor: '#2563eb',
      itemColor: '#64748b',
    },
  },
}

// 渲染应用
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider locale={zhCN} theme={themeConfig}>
          <AntdApp>
            <App />
          </AntdApp>
        </ConfigProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)

if (import.meta.env.DEV) {
  console.log(
    '%c🏥 智能医疗管家平台 %cv3.0',
    'color: #2563eb; font-size: 20px; font-weight: bold;',
    'color: #94a3b8; font-size: 12px;'
  )
}
