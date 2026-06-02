import React from 'react'
import { Modal, Space } from 'antd'
import { ExclamationCircleOutlined, CheckCircleOutlined, InfoCircleOutlined } from '@ant-design/icons'

export type ConfirmType = 'warning' | 'info' | 'success' | 'error'

interface ConfirmModalProps {
  visible: boolean
  title: string
  content: React.ReactNode
  type?: ConfirmType
  okText?: string
  cancelText?: string
  loading?: boolean
  onOk: () => void
  onCancel: () => void
}

const typeConfig = {
  warning: { icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />, okButtonProps: { danger: true } },
  info: { icon: <InfoCircleOutlined style={{ color: '#1890ff' }} />, okButtonProps: {} },
  success: { icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />, okButtonProps: {} },
  error: { icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />, okButtonProps: { danger: true } },
}

/**
 * ConfirmModal - 通用确认对话框
 *
 * 功能：
 * - 多种类型（warning/info/success/error）
 * - 无障碍支持（ARIA属性）
 * - 加载状态
 * - 键盘导航支持
 */
export function ConfirmModal({
  visible,
  title,
  content,
  type = 'warning',
  okText = '确认',
  cancelText = '取消',
  loading = false,
  onOk,
  onCancel,
}: ConfirmModalProps) {
  const config = typeConfig[type]

  return (
    <Modal
      open={visible}
      title={
        <Space>
          {config.icon}
          <span>{title}</span>
        </Space>
      }
      onOk={onOk}
      onCancel={onCancel}
      confirmLoading={loading}
      okText={okText}
      cancelText={cancelText}
      okButtonProps={config.okButtonProps}
      centered
      aria-labelledby="confirm-title"
      aria-describedby="confirm-content"
    >
      <div id="confirm-content">{content}</div>
    </Modal>
  )
}
