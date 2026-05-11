import React from 'react'

interface SkeletonLoaderProps {
  /** 骨架屏类型 */
  variant?: 'card' | 'list' | 'table' | 'chat' | 'detail'
  /** 行数 */
  lines?: number
  /** 是否显示头像 */
  showAvatar?: boolean
  /** 自定义样式 */
  style?: React.CSSProperties
}

/**
 * 骨架屏加载组件
 * 提供多种场景的骨架屏占位效果
 */
export default function SkeletonLoader({
  variant = 'card',
  lines = 3,
  showAvatar = false,
  style,
}: SkeletonLoaderProps) {
  // 卡片骨架屏
  if (variant === 'card') {
    return (
      <div className="skeleton" style={{
        borderRadius: '18px',
        padding: '24px',
        ...style,
      }}>
        {/* 标题 */}
        <div className="skeleton skeleton-title" style={{ width: '40%' }} />
        
        {/* 内容行 */}
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className="skeleton skeleton-text" style={{
            width: i === lines - 1 ? '60%' : '100%',
          }} />
        ))}

        {/* 底部操作区 */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
          <div className="skeleton" style={{ width: '80px', height: '36px', borderRadius: '10px' }} />
          <div className="skeleton" style={{ width: '80px', height: '36px', borderRadius: '10px' }} />
        </div>
      </div>
    )
  }

  // 列表骨架屏
  if (variant === 'list') {
    return (
      <div style={style}>
        {Array.from({ length: lines }).map((_, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '16px 0',
              borderBottom: idx < lines - 1 ? '1px solid var(--border-color)' : 'none',
            }}
          >
            {showAvatar && <div className="skeleton skeleton-avatar" />}
            <div style={{ flex: 1 }}>
              <div className="skeleton skeleton-text" style={{ width: '45%', marginBottom: '8px' }} />
              <div className="skeleton skeleton-text" style={{ width: '70%' }} />
            </div>
            <div className="skeleton" style={{ width: '60px', height: '28px', borderRadius: '14px' }} />
          </div>
        ))}
      </div>
    )
  }

  // 表格骨架屏
  if (variant === 'table') {
    return (
      <div style={style}>
        {/* 表头 */}
        <div style={{
          display: 'flex',
          gap: '16px',
          padding: '14px 16px',
          background: 'var(--background-warm)',
          borderRadius: '12px',
          marginBottom: '4px',
        }}>
          {[35, 25, 20, 20].map((width, i) => (
            <div key={i} className="skeleton" style={{ width: `${width}%`, height: '14px', borderRadius: '4px' }} />
          ))}
        </div>

        {/* 表体行 */}
        {Array.from({ length: Math.min(lines, 5) }).map((_, rowIdx) => (
          <div
            key={rowIdx}
            style={{
              display: 'flex',
              gap: '16px',
              padding: '14px 16px',
              borderBottom: rowIdx < lines - 1 ? '1px solid var(--divider-color)' : 'none',
            }}
          >
            {[35, 25, 20, 20].map((width, colIdx) => (
              <div key={colIdx} className="skeleton" style={{ width: `${width}%`, height: '14px', borderRadius: '4px' }} />
            ))}
          </div>
        ))}
      </div>
    )
  }

  // 聊天骨架屏
  if (variant === 'chat') {
    return (
      <div style={{ padding: '20px', ...style }}>
        {/* 用户消息 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px' }}>
          <div style={{ maxWidth: '60%' }}>
            <div className="skeleton" style={{ height: '48px', borderRadius: '18px' }} />
          </div>
        </div>

        {/* AI回复 */}
        <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '20px' }}>
          <div style={{ maxWidth: '75%' }}>
            <div className="skeleton" style={{ height: '32px', borderRadius: '18px', marginBottom: '8px' }} />
            <div className="skeleton" style={{ height: '56px', borderRadius: '18px', marginBottom: '8px' }} />
            <div className="skeleton" style={{ height: '40px', borderRadius: '18px', width: '60%' }} />
          </div>
        </div>

        {/* 另一组对话 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px' }}>
          <div style={{ maxWidth: '50%' }}>
            <div className="skeleton" style={{ height: '44px', borderRadius: '18px' }} />
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
          <div style={{ maxWidth: '65%' }}>
            <div className="skeleton" style={{ height: '64px', borderRadius: '18px' }} />
          </div>
        </div>
      </div>
    )
  }

  // 详情页骨架屏
  if (variant === 'detail') {
    return (
      <div style={style}>
        {/* 头部 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '28px' }}>
          <div className="skeleton skeleton-avatar" style={{ width: '72px', height: '72px' }} />
          <div style={{ flex: 1 }}>
            <div className="skeleton skeleton-title" style={{ width: '30%', marginBottom: '10px' }} />
            <div className="skeleton skeleton-text" style={{ width: '50%' }} />
          </div>
          <div className="skeleton" style={{ width: '100px', height: '38px', borderRadius: '12px' }} />
        </div>

        {/* 内容区 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: '120px', borderRadius: '16px' }} />
          ))}
        </div>

        {/* 详情描述 */}
        <div style={{ marginTop: '24px' }}>
          <div className="skeleton skeleton-title" style={{ width: '15%', marginBottom: '16px' }} />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton skeleton-text" style={{
              width: i === 4 ? '55%' : '100%',
            }} />
          ))}
        </div>
      </div>
    )
  }

  return null
}

export function CardSkeleton() {
  return <SkeletonLoader variant="card" lines={4} />
}

export function ListSkeleton({ count = 5 }: { count?: number }) {
  return <SkeletonLoader variant="list" lines={count} showAvatar />
}

export function ChatSkeleton() {
  return <SkeletonLoader variant="chat" />
}
