import { Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'

interface PageLoadingProps {
  tip?: string
  size?: 'small' | 'default' | 'large'
  fullScreen?: boolean
}

/**
 * 全局页面加载组件
 * 提供统一的加载状态展示，支持全屏和局部模式
 */
export default function PageLoading({
  tip = '正在加载...',
  size = 'large',
  fullScreen = false,
}: PageLoadingProps) {
  const spinner = (
    <Spin
      indicator={<LoadingOutlined style={{ fontSize: size === 'large' ? 32 : size === 'default' ? 24 : 16, color: '#2563eb' }} spin />}
      size={size}
    />
  )

  if (fullScreen) {
    return (
      <div style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(248, 250, 252, 0.95)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        gap: '16px',
      }}>
        {/* Logo动画 */}
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '16px',
          background: 'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 8px 24px rgba(37, 99, 235, 0.2)',
          animation: 'pulse 1.5s ease-in-out infinite',
        }}>
          <LoadingOutlined style={{ fontSize: '24px', color: '#fff' }} spin />
        </div>

        <span style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          fontWeight: 500,
        }}>
          {tip}
        </span>

        {/* 加载进度条 */}
        <div style={{
          width: '180px',
          height: '3px',
          borderRadius: '2px',
          background: 'var(--gray-200)',
          overflow: 'hidden',
        }}>
          <div style={{
            width: '40%',
            height: '100%',
            borderRadius: '2px',
            background: 'linear-gradient(90deg, #2563eb, #0d9488)',
            animation: 'loadingProgress 1.5s ease-in-out infinite',
          }} />
        </div>
      </div>
    )
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 20px',
      gap: '12px',
      minHeight: '240px',
    }}>
      {spinner}
      {tip && (
        <span style={{
          fontSize: '13px',
          color: 'var(--text-hint)',
          fontWeight: 500,
        }}>
          {tip}
        </span>
      )}
    </div>
  )
}
