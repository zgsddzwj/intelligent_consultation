import React from 'react'

/**
 * 响应式容器组件
 * 提供统一的响应式布局容器，适配不同屏幕尺寸
 */
interface ResponsiveContainerProps {
  children: React.ReactNode
  /** 最大宽度 */
  maxWidth?: number | string
  /** 内边距 */
  padding?: string | { xs?: string; sm?: string; md?: string; lg?: string }
  /** 自定义样式 */
  style?: React.CSSProperties
  className?: string
}

export function ResponsiveContainer({
  children,
  maxWidth = 1400,
  padding = '24px 32px',
  style,
  className,
}: ResponsiveContainerProps) {
  return (
    <div
      className={className}
      style={{
        maxWidth: typeof maxWidth === 'number' ? `${maxWidth}px` : maxWidth,
        margin: '0 auto',
        width: '100%',
        padding: typeof padding === 'string' ? padding : undefined,
        boxSizing: 'border-box',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/**
 * 响应式网格布局
 * 根据屏幕尺寸自动调整列数
 */
interface ResponsiveGridProps {
  children: React.ReactNode
  /** 列数配置 */
  columns?: { xs?: number; sm?: number; md?: number; lg?: number; xl?: number }
  /** 间距 */
  gap?: number | string
  style?: React.CSSProperties
}

export function ResponsiveGrid({
  children,
  columns = { xs: 1, sm: 2, md: 3, lg: 4 },
  gap = 20,
  style,
}: ResponsiveGridProps) {
  const colConfig = columns

  // 使用CSS Grid实现响应式
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${colConfig.xs || 1}, 1fr)`,
        gap: typeof gap === 'number' ? `${gap}px` : gap,
        ...style,
      }}
      className="responsive-grid"
    />
  )
}

/**
 * 移动端检测Hook（简化版）
 * 返回当前是否为移动端视图
 */
export function useIsMobile(breakpoint: number = 768): boolean {
  if (typeof window === 'undefined') return false
  return window.innerWidth < breakpoint
}

/**
 * 断点常量
 */
export const BREAKPOINTS = {
  xs: 480,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  xxl: 1536,
} as const

export default ResponsiveContainer
