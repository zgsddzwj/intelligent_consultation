import { Empty, Button, Typography } from 'antd'
import type { EmptyProps } from 'antd'
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'

const { Text } = Typography

interface EmptyStateProps extends Omit<EmptyProps, 'image'> {
  /** 空状态类型 */
  variant?: 'default' | 'data' | 'search' | 'error' | 'chat'
  /** 描述文字 */
  description?: string
  /** 操作按钮文字 */
  actionText?: string
  /** 操作回调 */
  onAction?: () => void
  /** 是否显示刷新按钮 */
  showRefresh?: boolean
  onRefresh?: () => void
}

/**
 * 统一空状态组件
 * 支持多种场景：数据为空、搜索无结果、错误等
 */
export default function EmptyState({
  variant = 'default',
  description,
  actionText,
  onAction,
  showRefresh = false,
  onRefresh,
  style,
  ...restProps
}: EmptyStateProps) {
  const configs = {
    default: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '暂无数据',
      icon: null,
    },
    data: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '还没有任何内容，快来创建第一条吧',
      icon: <PlusOutlined />,
    },
    search: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '没有找到匹配的结果，请尝试其他关键词',
      icon: <SearchOutlined />,
    },
    error: {
      image: Empty.PRESENTED_IMAGE_DEFAULT,
      description: description || '加载失败，请检查网络后重试',
      icon: null,
    },
    chat: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '开始一段新的对话吧',
      icon: null,
    },
  }

  const config = configs[variant]

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '48px 24px',
      minHeight: '300px',
      animation: 'fadeIn 0.4s ease-out',
      ...style,
    }}>
      {/* 图标区域 */}
      {config.icon && (
        <div style={{
          width: '72px',
          height: '72px',
          borderRadius: '20px',
          background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '20px',
          fontSize: '28px',
          color: '#667eea',
          border: '1px solid rgba(102, 126, 234, 0.15)',
        }}>
          {config.icon}
        </div>
      )}

      <Empty
        {...restProps}
        image={config.image}
        description={
          <span style={{ color: '#8e8ea0', fontSize: '14px', lineHeight: 1.6 }}>
            {config.description}
          </span>
        }
      />

      {/* 操作按钮区 */}
      {(actionText && onAction) && (
        <Button
          type="primary"
          icon={variant === 'data' ? <PlusOutlined /> : undefined}
          onClick={onAction}
          style={{
            marginTop: '20px',
            borderRadius: '12px',
            fontWeight: 600,
            paddingLeft: '24px',
            paddingRight: '24px',
            height: '44px',
          }}
        >
          {actionText}
        </Button>
      )}

      {showRefresh && (
        <Button
          icon={<ReloadOutlined />}
          onClick={onRefresh}
          style={{
            marginTop: actionText ? '12px' : '20px',
            borderRadius: '12px',
            color: '#667eea',
            borderColor: '#667eea',
          }}
        >
          刷新重试
        </Button>
      )}
    </div>
  )
}
