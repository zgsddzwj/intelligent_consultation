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
      // 数据过期时间：5分钟
      staleTime: 5 * 60 * 1000,
      // 缓存时间：10分钟
      gcTime: 10 * 60 * 1000,
      // 失败重试次数
      retry: 2,
      // 重试延迟（指数退避）
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // 窗口聚焦时是否重新请求
      refetchOnWindowFocus: false,
      // 离线时不重新请求
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
      // 失败后回滚
      onSettled: (_data, error) => {
        if (error) {
          console.warn('[Mutation] 操作失败:', error)
        }
      },
    },
  },
})

// Ant Design 全局主题配置 v2.0
const themeConfig = {
  algorithm: theme.defaultAlgorithm,
  
  token: {
    // ===== 主色调系统 =====
    colorPrimary: '#667eea',
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorInfo: '#3b82f6',
    
    // ===== 圆角系统 =====
    borderRadius: 8,
    borderRadiusLG: 16,
    borderRadiusSM: 6,
    borderRadiusXS: 4,
    
    // ===== 字体系统 =====
    fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 
      'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, 
      Arial, sans-serif`,
    fontSize: 15,
    fontSizeLG: 17,
    fontSizeSM: 13,
    fontSizeXL: 20,
    
    // ===== 阴影系统 =====
    boxShadow: '0 4px 16px rgba(102, 126, 234, 0.12)',
    boxShadowSecondary: '0 2px 8px rgba(0, 0, 0, 0.06)',
    
    // ===== 动画 =====
    motionDurationMid: '0.3s',
    motionDurationSlow: '0.5s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    motionEaseOut: 'cubic-bezier(0, 0, 0.2, 1)',
    
    // ===== 间距 =====
    padding: 16,
    paddingLG: 24,
    paddingSM: 12,
    paddingXS: 8,
    
    // ===== 控件高度 =====
    controlHeight: 44,
    controlHeightLG: 52,
    controlHeightSM: 32,
    
    // ===== 线宽 =====
    lineWidth: 1,
    lineWidthBold: 2,
    
    // ===== 其他 =====
    wireframe: false,
  },
  
  components: {
    // 按钮组件
    Button: {
      primaryShadow: '0 4px 20px rgba(102, 126, 234, 0.35)',
      defaultBg: 'transparent',
      contentFontSizeLG: 17,
      fontWeight: 600,
    },
    
    // 输入框组件
    Input: {
      controlHeight: 48,
      paddingInline: 16,
      activeBorderColor: '#667eea',
      hoverBorderColor: '#8b9cf7',
      activeShadow: '0 0 0 4px rgba(102, 126, 234, 0.08)',
    },
    
    Textarea: {
      controlHeight: 120,
      paddingInline: 16,
    },
    
    // 卡片组件
    Card: {
      borderRadiusLG: 20,
      boxShadowTertiary: '0 4px 24px rgba(0, 0, 0, 0.06)',
      paddingLG: 24,
    },
    
    // 消息提示
    Message: {
      contentBg: '#ffffff',
      contentPaddingMD: '14px 22px',
    },
    
    // 标签
    Tag: {
      borderRadiusSM: 20,
    },
    
    // 选择器
    Select: {
      optionSelectedBg: 'rgba(102, 126, 234, 0.08)',
    },
    
    // 表格
    Table: {
      headerBg: '#fafbff',
      rowHoverBg: 'rgba(102, 126, 234, 0.04)',
      borderColor: 'rgba(0, 0, 0, 0.04)',
      headerBorderRadius: 12,
    },
    
    // Modal弹窗
    Modal: {
      borderRadiusLG: 20,
      headerBg: 'linear-gradient(135deg, #fafbff, #f5f0ff)',
    },
    
    // 导航菜单
    Menu: {
      itemBorderRadius: 10,
      itemMarginBlock: 4,
      itemMarginInline: 8,
      iconSize: 18,
      itemActiveBg: 'rgba(102, 126, 234, 0.1)',
      itemHoverBg: 'rgba(102, 126, 234, 0.05)',
    },
    
    // 布局
    Layout: {
      headerPadding: '0 28px',
      bodyPadding: 24,
      footerPadding: '16px 28px',
    },
    
    // 列表
    List: {
      itemPadding: '14px 0',
    },
    
    // 进度条
    Progress: {
      defaultColor: '#667eea',
      remainingColor: 'rgba(0, 0, 0, 0.04)',
    },
    
    // 徽标
    Badge: {
      dotSize: 8,
      indicatorHeight: 20,
      indicatorHeightSM: 16,
    },
    
    // 头像
    Avatar: {
      containerSize: 40,
      containerSizeLG: 48,
      containerSizeSM: 32,
    },
    
    // 统计数字
    Statistic: {
      contentFontSize: 26,
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

// 开发环境下的性能监控和品牌展示
if (import.meta.env.DEV) {
  console.log(
    '%c🏥 智能医疗管家平台 %cv2.0',
    'color: #667eea; font-size: 22px; font-weight: bold; text-shadow: 0 1px 2px rgba(102,126,234,0.2);',
    'color: #999; font-size: 13px;'
  )
  console.log(
    '%c⚡ 技术栈: React 18 + TypeScript + Vite + Ant Design 5 + TanStack Query + Zustand',
    'color: #10b981; font-size: 12px;'
  )
  console.log(
    '%c⚠️ 开发模式 - 请勿在生产环境使用此控制台',
    'color: #f59e0b; font-size: 12px;'
  )
}
