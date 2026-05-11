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
      indicator={<LoadingOutlined style={{ fontSize: size === 'large' ? 36 : size === 'default' ? 24 : 16, color: '#667eea' }} spin />}
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
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        gap: '20px',
      }}>
        {/* Logo动画 */}
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '18px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)',
          animation: 'pulse 1.5s ease-in-out infinite',
        }}>
          <LoadingOutlined style={{ fontSize: '28px', color: '#fff' }} spin />
        </div>
        
        <span style={{
          fontSize: '15px',
          color: '#666',
          fontWeight: 500,
          letterSpacing: '0.02em',
        }}>
          {tip}
        </span>

        {/* 加载进度条 */}
        <div style={{
          width: '200px',
          height: '3px',
          borderRadius: '2px',
          background: 'rgba(102, 126, 234, 0.15)',
          overflow: 'hidden',
        }}>
          <div style={{
            width: '40%',
            height: '100%',
            borderRadius: '2px',
            background: 'linear-gradient(90deg, #667eea, #764ba2)',
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
      padding: '60px 20px',
      gap: '16px',
      minHeight: '300px',
    }}>
      {spinner}
      {tip && (
        <span style={{
          fontSize: '14px',
          color: '#8e8ea0',
          fontWeight: 500,
        }}>
          {tip}
        </span>
      )}
    </div>
  )
}
