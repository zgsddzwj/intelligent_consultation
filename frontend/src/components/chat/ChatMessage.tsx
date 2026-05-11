import React from 'react'
import { Avatar } from 'antd'
import { UserOutlined, RobotOutlined } from '@ant-design/icons'
import type { Message, RiskLevel } from '../../types/chat'

interface ChatMessageProps {
  message: Message
}

/** 根据风险等级返回中文标签 */
function getRiskLabel(level: RiskLevel): string {
  const map: Record<RiskLevel, string> = {
    high: '高风险',
    medium: '中等风险',
    low: '低风险',
  }
  return map[level] || level
}

function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '20px',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '0 16px',
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
          maxWidth: '70%',
        }}
      >
        <div
          style={{
            padding: '16px 20px',
            borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
            background: isUser
              ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
              : '#ffffff',
            color: isUser ? '#fff' : '#333',
            boxShadow: isUser
              ? '0 4px 20px rgba(102, 126, 234, 0.4)'
              : '0 2px 12px rgba(0, 0, 0, 0.08)',
            border: isUser ? 'none' : '1px solid rgba(0, 0, 0, 0.05)',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
            position: 'relative',
            fontSize: '15px',
            lineHeight: '1.6',
          }}
        >
          {message.content}

          {/* 信息来源 */}
          {message.sources && message.sources.length > 0 && (
            <div
              style={{
                marginTop: '12px',
                paddingTop: '8px',
                borderTop: `1px solid ${isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'}`,
                fontSize: '12px',
                opacity: 0.8,
              }}
            >
              📚 <strong>信息来源:</strong> {message.sources.join(', ')}
            </div>
          )}

          {/* 风险等级标签 */}
          {message.risk_level && (
            <div
              style={{
                marginTop: '8px',
                padding: '4px 8px',
                borderRadius: '12px',
                background: '#ff4d4f',
                color: 'white',
                fontSize: '11px',
                display: 'inline-block',
                fontWeight: 'bold',
              }}
            >
              ⚠️ {getRiskLabel(message.risk_level as RiskLevel)}
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
    </div>
  )
}

export default React.memo(ChatMessage)
