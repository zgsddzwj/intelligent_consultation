import { Empty, Button, Typography } from 'antd'
import type { EmptyProps } from 'antd'
import {
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  MessageOutlined,
  InboxOutlined,
  WarningOutlined,
} from '@ant-design/icons'

const { Text } = Typography

interface EmptyStateProps extends Omit<EmptyProps, 'image'> {
  /** 空状态类型 */
  variant?: 'default' | 'data' | 'search' | 'error' | 'chat' | 'notification'
  /** 描述文字 */
  description?: string
  /** 操作按钮文字 */
  actionText?: string
  /** 操作回调 */
  onAction?: () => void
  /** 是否显示刷新按钮 */
  showRefresh?: boolean
  onRefresh?: () => void
  /** 自定义图标 */
  customIcon?: React.ReactNode
}

/**
 * 统一空状态组件 - 增强版
 * 支持多种场景：数据为空、搜索无结果、错误、聊天、通知等
 */
export default function EmptyState({
  variant = 'default',
  description,
  actionText,
  onAction,
  showRefresh = false,
  onRefresh,
  customIcon,
  style,
  ...restProps
}: EmptyStateProps) {
  const configs = {
    default: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '暂无数据',
      icon: <InboxOutlined />,
      iconBg: 'rgba(102, 126, 234, 0.08)',
      iconColor: '#667eea',
    },
    data: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '还没有任何内容，快来创建第一条吧',
      icon: <PlusOutlined />,
      iconBg: 'rgba(82, 196, 26, 0.08)',
      iconColor: '#52c41a',
    },
    search: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '没有找到匹配的结果，请尝试其他关键词',
      icon: <SearchOutlined />,
      iconBg: 'rgba(250, 173, 20, 0.08)',
      iconColor: '#faad14',
    },
    error: {
      image: Empty.PRESENTED_IMAGE_DEFAULT,
      description: description || '加载失败，请检查网络后重试',
      icon: <WarningOutlined />,
      iconBg: 'rgba(255, 77, 79, 0.08)',
      iconColor: '#ff4d4f',
    },
    chat: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '开始一段新的对话吧',
      icon: <MessageOutlined />,
      iconBg: 'rgba(102, 126, 234, 0.08)',
      iconColor: '#667eea',
    },
    notification: {
      image: Empty.PRESENTED_IMAGE_SIMPLE,
      description: description || '暂无通知',
      icon: <InboxOutlined />,
      iconBg: 'rgba(142, 142, 160, 0.08)',
      iconColor: '#8e8ea0',
    },
  }

  const config = configs[variant]

  return (
    <div
      className="animate-fade-in-up"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        minHeight: '280px',
        ...style,
      }}
    >
      {/* 图标区域 */}
      {(customIcon || config.icon) && (
        <div
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '24px',
            background: config.iconBg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '24px',
            fontSize: '32px',
            color: config.iconColor,
            border: `1px solid ${config.iconBg.replace('0.08', '0.15')}`,
            transition: 'all var(--transition-normal)',
          }}
        >
          {customIcon || config.icon}
        </div>
      )}

      <Empty
        {...restProps}
        image={config.image}
        description={
          <Text
            style={{
              color: 'var(--text-hint)',
              fontSize: '14px',
              lineHeight: 1.6,
            }}
          >
            {config.description}
          </Text>
        }
      />

      {/* 操作按钮区 */}
      <div
        style={{
          display: 'flex',
          gap: '12px',
          marginTop: '20px',
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        {actionText && onAction && (
          <Button
            type="primary"
            icon={variant === 'data' ? <PlusOutlined /> : undefined}
            onClick={onAction}
            style={{
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
              borderRadius: '12px',
              color: 'var(--primary-color)',
              borderColor: 'var(--primary-color)',
              height: '44px',
            }}
          >
            刷新重试
          </Button>
        )}
      </div>
    </div>
  )
}
