import React, { useState } from 'react'
import { Avatar, Tag, Tooltip, Button } from 'antd'
import { UserOutlined, RobotOutlined, CopyOutlined, CheckOutlined, ExclamationCircleFilled } from '@ant-design/icons'
import type { Message, RiskLevel } from '../../types/chat'

interface ChatMessageProps {
  message: Message
  index?: number
}

/** 根据风险等级返回中文标签和颜色 */
function getRiskInfo(level: RiskLevel): { label: string; color: string; bg: string } {
  const map: Record<RiskLevel, { label: string; color: string; bg: string }> = {
    high: { label: '高风险', color: '#ff4d4f', bg: '#fff2f0' },
    medium: { label: '中等风险', color: '#faad14', bg: '#fffbe6' },
    low: { label: '低风险', color: '#52c41a', bg: '#f6ffed' },
  }
  return map[level] || { label: level, color: '#999', bg: '#f5f5f5' }
}

function ChatMessage({ message, index = 0 }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const animationDelay = Math.min(index * 80, 400)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // 复制失败静默处理
    }
  }

  return (
    <div
      className="animate-fade-in-up"
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '20px',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '0 16px',
        animationDelay: `${animationDelay}ms`,
        opacity: 0,
      }}
    >
      {/* AI 头像 */}
      {!isUser && (
        <Avatar
          icon={<RobotOutlined />}
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            flexShrink: 0,
            boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)',
          }}
          size={40}
        />
      )}

      {/* 消息内容 */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start',
          maxWidth: '72%',
          minWidth: '80px',
        }}
      >
        {/* 时间戳 */}
        <span
          style={{
            fontSize: '11px',
            color: 'var(--text-hint)',
            marginBottom: '4px',
            padding: '0 4px',
          }}
        >
          {message.timestamp
            ? new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
            : new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </span>

        <div
          style={{
            padding: '14px 18px',
            borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
            background: isUser
              ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
              : 'var(--background-white)',
            color: isUser ? '#fff' : 'var(--text-primary)',
            boxShadow: isUser
              ? '0 4px 20px rgba(102, 126, 234, 0.4)'
              : 'var(--shadow-sm)',
            border: isUser ? 'none' : '1px solid var(--border-color)',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
            position: 'relative',
            fontSize: '15px',
            lineHeight: '1.65',
            transition: 'all var(--transition-normal)',
          }}
        >
          {/* 复制按钮（仅AI消息） */}
          {!isUser && (
            <Tooltip title={copied ? '已复制' : '复制内容'}>
              <Button
                type="text"
                size="small"
                icon={copied ? <CheckOutlined style={{ color: '#52c41a' }} /> : <CopyOutlined />}
                onClick={handleCopy}
                style={{
                  position: 'absolute',
                  top: '8px',
                  right: '8px',
                  opacity: 0,
                  transition: 'opacity var(--transition-fast)',
                  padding: '2px 6px',
                  height: 'auto',
                }}
                className="message-copy-btn"
              />
            </Tooltip>
          )}

          {message.content}

          {/* 信息来源 */}
          {message.sources && message.sources.length > 0 && (
            <div
              style={{
                marginTop: '12px',
                paddingTop: '10px',
                borderTop: `1px solid ${isUser ? 'rgba(255, 255, 255, 0.2)' : 'var(--border-color)'}`,
                fontSize: '12px',
                opacity: 0.85,
              }}
            >
              <span style={{ fontWeight: 600 }}>📚 信息来源:</span>{' '}
              {message.sources.map((s, i) => (
                <Tag
                  key={i}
                  size="small"
                  style={{
                    margin: '2px 4px 2px 0',
                    fontSize: '11px',
                    background: isUser ? 'rgba(255,255,255,0.15)' : 'var(--primary-50)',
                    color: isUser ? '#fff' : 'var(--primary-600)',
                    border: 'none',
                  }}
                >
                  {s}
                </Tag>
              ))}
            </div>
          )}

          {/* 风险等级标签 */}
          {message.risk_level && (
            <div style={{ marginTop: '10px' }}>
              <Tag
                icon={<ExclamationCircleFilled />}
                style={{
                  background: getRiskInfo(message.risk_level as RiskLevel).bg,
                  color: getRiskInfo(message.risk_level as RiskLevel).color,
                  border: `1px solid ${getRiskInfo(message.risk_level as RiskLevel).color}`,
                  fontWeight: 600,
                  fontSize: '12px',
                  padding: '2px 10px',
                }}
              >
                {getRiskInfo(message.risk_level as RiskLevel).label}
              </Tag>
            </div>
          )}
        </div>
      </div>

      {/* 用户头像 */}
      {isUser && (
        <Avatar
          icon={<UserOutlined />}
          style={{
            background: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)',
            flexShrink: 0,
            boxShadow: '0 4px 12px rgba(82, 196, 26, 0.3)',
          }}
          size={40}
        />
      )}

      <style>{`
        .message-copy-btn {
          opacity: 0 !important;
        }
        div:hover > .message-copy-btn,
        div:hover .message-copy-btn {
          opacity: 0.6 !important;
        }
        div:hover > .message-copy-btn:hover,
        div:hover .message-copy-btn:hover {
          opacity: 1 !important;
          background: var(--primary-50) !important;
        }
      `}</style>
    </div>
  )
}

export default React.memo(ChatMessage)
