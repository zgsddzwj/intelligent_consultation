import { useState, memo } from 'react'
import { Avatar, Tag, Tooltip, Button } from 'antd'
import { UserOutlined, RobotOutlined, CopyOutlined, CheckOutlined, ExclamationCircleFilled } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message, RiskLevel } from '../../types/chat'
import ThinkingPanel from './ThinkingPanel'
import VoicePlayer from '../voice/VoicePlayer'

interface ChatMessageProps {
  message: Message
  index?: number
}

/** 根据风险等级返回中文标签和颜色 */
function getRiskInfo(level: RiskLevel): { label: string; color: string; bg: string } {
  const map: Record<RiskLevel, { label: string; color: string; bg: string }> = {
    high: { label: '高风险', color: '#dc2626', bg: '#fef2f2' },
    medium: { label: '中等风险', color: '#d97706', bg: '#fffbeb' },
    low: { label: '低风险', color: '#16a34a', bg: '#f0fdf4' },
  }
  return map[level] || { label: level, color: '#64748b', bg: '#f8fafc' }
}

function ChatMessage({ message, index = 0 }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const animationDelay = Math.min(index * 60, 300)

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
      className="chat-message-wrapper animate-fade-in-up"
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '16px',
        alignItems: 'flex-start',
        gap: '10px',
        padding: '0 24px',
        animationDelay: `${animationDelay}ms`,
        opacity: 0,
      }}
    >
      {/* AI 头像 */}
      {!isUser && (
        <Avatar
          icon={<RobotOutlined />}
          style={{
            background: 'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
            flexShrink: 0,
            boxShadow: '0 2px 8px rgba(37, 99, 235, 0.2)',
          }}
          size={36}
        />
      )}

      {/* 消息内容 */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start',
          maxWidth: '70%',
          minWidth: '60px',
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

        {/* 思考过程面板（DeepSeek 风格可折叠） */}
        {!isUser && message.thinkingSteps && message.thinkingSteps.length > 0 && (
          <ThinkingPanel steps={message.thinkingSteps} isThinking={message.isThinking} />
        )}

        {/* 消息气泡：思考中且无内容时不渲染，避免空白框 */}
        {(!message.isThinking || message.content) && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: isUser ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
            background: isUser
              ? 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)'
              : 'var(--background-white)',
            color: isUser ? '#fff' : 'var(--text-primary)',
            boxShadow: isUser
              ? '0 2px 10px rgba(37, 99, 235, 0.2)'
              : 'var(--shadow-sm)',
            border: isUser ? 'none' : '1px solid var(--border-color)',
            wordBreak: 'break-word',
            whiteSpace: isUser ? 'pre-wrap' : 'normal',
            position: 'relative',
            fontSize: '14px',
            lineHeight: 1.6,
          }}
        >
          {/* AI 消息用 Markdown 渲染，用户消息用纯文本 */}
          {isUser ? (
            message.content
          ) : (
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* 信息来源 */}
          {message.sources && message.sources.length > 0 && (
            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop: `1px solid ${isUser ? 'rgba(255, 255, 255, 0.2)' : 'var(--border-color)'}`,
                fontSize: '12px',
                opacity: 0.85,
              }}
            >
              <span style={{ fontWeight: 600 }}>信息来源:</span>{' '}
              {message.sources.map((s, i) => (
                <Tag
                  key={i}
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
            <div style={{ marginTop: '8px' }}>
              <Tag
                icon={<ExclamationCircleFilled />}
                style={{
                  background: getRiskInfo(message.risk_level as RiskLevel).bg,
                  color: getRiskInfo(message.risk_level as RiskLevel).color,
                  border: `1px solid ${getRiskInfo(message.risk_level as RiskLevel).color}`,
                  fontWeight: 600,
                  fontSize: '11px',
                  padding: '2px 8px',
                }}
              >
                {getRiskInfo(message.risk_level as RiskLevel).label}
              </Tag>
            </div>
          )}
        </div>
        )}

        {/* AI 消息底部操作栏（豆包风格：播放语音 + 复制） */}
        {!isUser && message.content && !message.isStreaming && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginTop: '4px',
              padding: '0 4px',
            }}
          >
            <VoicePlayer text={message.content} messageId={message.id} />
            <Tooltip title={copied ? '已复制' : '复制内容'}>
              <Button
                type="text"
                size="small"
                className="copy-btn"
                icon={copied ? <CheckOutlined style={{ color: '#16a34a' }} /> : <CopyOutlined />}
                onClick={handleCopy}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '2px 8px',
                  height: '28px',
                  fontSize: '12px',
                  color: copied ? '#16a34a' : '#94a3b8',
                }}
              >
                <span>{copied ? '已复制' : '复制'}</span>
              </Button>
            </Tooltip>
          </div>
        )}
      </div>

      {/* 用户头像 */}
      {isUser && (
        <Avatar
          icon={<UserOutlined />}
          style={{
            background: 'linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)',
            flexShrink: 0,
            boxShadow: '0 2px 8px rgba(13, 148, 136, 0.2)',
          }}
          size={36}
        />
      )}
    </div>
  )
}

export default memo(ChatMessage)
