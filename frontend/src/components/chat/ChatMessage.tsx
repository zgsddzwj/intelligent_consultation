import { memo, useState, useMemo, useCallback } from 'react'
import { Avatar, Tag, Tooltip, Button } from 'antd'
import { UserOutlined, RobotOutlined, CopyOutlined, CheckOutlined, ExclamationCircleFilled, LinkOutlined, InfoCircleOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message, RiskLevel, SourceRef } from '../../types/chat'
import ThinkingPanel from './ThinkingPanel'
import VoicePlayer from '../voice/VoicePlayer'

interface ChatMessageProps {
  message: Message
  index?: number
}

/** 匹配内联来源标注，如 [来源：xxx] / [来源:xxx] / [来源1]xxx / [来源N：xxx] */
function matchInlineSources(content: string): { cleaned: string; sources: SourceRef[] } {
  const sources: SourceRef[] = []
  const seen = new Set<string>()

  // 每次都创建新的 RegExp 实例，避免 g 标志的 lastIndex 复用问题
  const re = /\[来源\s*\d*\s*[：:]\s*([^\]]+?)\]/g

  const cleaned = content.replace(re, (_match, title: string) => {
    const t = title.trim()
    if (t && !seen.has(t)) {
      seen.add(t)
      sources.push({ title: t })
    }
    return ''
  })

  return { cleaned, sources }
}

/** 匹配独立的免责声明段（以"免责声明"或"本回答仅供参考"开头的行） */
function matchDisclaimer(content: string): { cleaned: string; disclaimer: string | null } {
  const re = /(?:\n+|^)\s*(?:【?免责声明】?[\s\S]*$|本回答仅供参考[\s\S]*$)$/
  const dMatch = content.match(re)
  if (dMatch) {
    return {
      cleaned: content.slice(0, dMatch.index).trim(),
      disclaimer: dMatch[0].trim(),
    }
  }
  return { cleaned: content, disclaimer: null }
}

/** 从正文内容中提取内联来源标注和免责声明，返回清洗后的正文和来源列表 */
function extractSourcesAndClean(content: string): {
  body: string
  inlineSources: SourceRef[]
  disclaimer: string | null
} {
  const { cleaned: s1, sources: inlineSources } = matchInlineSources(content)

  // 清理移除来源后可能残留的多余空格
  let cleaned = s1.replace(/[ \t]+\n/g, '\n').replace(/  +/g, ' ')

  // 提取免责声明
  const { cleaned: finalBody, disclaimer } = matchDisclaimer(cleaned)

  return { body: finalBody.trim(), inlineSources, disclaimer }
}

/** Markdown 渲染插件（模块级常量，保持引用稳定以复用解析管线） */
const REMARK_PLUGINS = [remarkGfm]

/** 根据风险等级返回中文标签和颜色 */
const RISK_INFO_MAP: Record<RiskLevel, { label: string; color: string; bg: string }> = {
  high: { label: '高风险', color: '#dc2626', bg: '#fef2f2' },
  medium: { label: '中等风险', color: '#d97706', bg: '#fffbeb' },
  low: { label: '低风险', color: '#16a34a', bg: '#f0fdf4' },
}

const DEFAULT_RISK_INFO = { label: '', color: '#64748b', bg: '#f8fafc' }

function ChatMessage({ message, index = 0 }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const animationDelay = Math.min(index * 60, 300)

  // 缓存风险信息，避免每次渲染重新创建对象
  const riskInfo = useMemo(
    () => RISK_INFO_MAP[message.risk_level as RiskLevel] || DEFAULT_RISK_INFO,
    [message.risk_level]
  )

  // 是否显示风险标签
  const showRiskTag = !!message.risk_level

  // 从 AI 回复中提取内联来源标注和免责声明，与 message.sources 合并
  const { body, allSources, disclaimer } = useMemo(() => {
    if (isUser) {
      return { body: message.content, allSources: [] as SourceRef[], disclaimer: null }
    }
    const { body: cleanedBody, inlineSources, disclaimer: d } = extractSourcesAndClean(message.content)
    // 合并来源：优先 SSE sources，补充内联提取的来源
    const seen = new Set<string>()
    const all: SourceRef[] = []
    for (const s of [...(message.sources || []), ...inlineSources]) {
      if (s.title && !seen.has(s.title)) {
        seen.add(s.title)
        all.push(s)
      }
    }
    return { body: cleanedBody, allSources: all, disclaimer: d }
  }, [message.content, message.sources, isUser])

  // 时间戳只依赖 message.timestamp 计算，避免流式期间每次重渲染都跳动
  const timeText = useMemo(
    () => new Date(message.timestamp ?? Date.now()).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    [message.timestamp]
  )

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(body || message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // 复制失败静默处理
    }
  }, [body, message.content])

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
          {timeText}
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
              <ReactMarkdown remarkPlugins={REMARK_PLUGINS}>
                {body}
              </ReactMarkdown>
            </div>
          )}

          {/* 风险等级标签 */}
          {showRiskTag && (
            <div style={{ marginTop: '8px' }}>
              <Tag
                icon={<ExclamationCircleFilled />}
                style={{
                  background: riskInfo.bg,
                  color: riskInfo.color,
                  border: `1px solid ${riskInfo.color}`,
                  fontWeight: 600,
                  fontSize: '11px',
                  padding: '2px 8px',
                }}
              >
                {riskInfo.label}
              </Tag>
            </div>
          )}
        </div>
        )}

        {/* 参考来源面板 —— 与正文视觉分离，独立卡片样式 */}
        {!isUser && allSources.length > 0 && (
          <div
            style={{
              marginTop: '6px',
              padding: '10px 14px',
              borderRadius: '10px',
              background: 'var(--primary-50, #eff6ff)',
              border: '1px solid var(--primary-100, #dbeafe)',
              maxWidth: '100%',
              width: '100%',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginBottom: '8px',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--primary-700, #1d4ed8)',
              }}
            >
              <LinkOutlined />
              <span>参考资料</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {allSources.map((s, i) => {
                const href = s.url || `https://www.google.com/search?q=${encodeURIComponent(s.title)}`
                return (
                  <a
                    key={i}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '3px 10px',
                      fontSize: '11px',
                      background: '#fff',
                      color: '#2563eb',
                      border: '1px solid #bfdbfe',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      textDecoration: 'none',
                      transition: 'all 0.2s',
                      maxWidth: '240px',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = '#eff6ff'
                      e.currentTarget.style.borderColor = '#2563eb'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = '#fff'
                      e.currentTarget.style.borderColor = '#bfdbfe'
                    }}
                  >
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      [{i + 1}] {s.title}
                    </span>
                    <LinkOutlined style={{ fontSize: '10px', opacity: 0.6, flexShrink: 0 }} />
                  </a>
                )
              })}
            </div>
          </div>
        )}

        {/* 免责声明 —— 独立面板，与正文区分 */}
        {!isUser && disclaimer && (
          <div
            style={{
              marginTop: '6px',
              padding: '8px 12px',
              borderRadius: '8px',
              background: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.2)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '6px',
              fontSize: '11px',
              color: '#92400e',
              lineHeight: 1.5,
            }}
          >
            <InfoCircleOutlined style={{ marginTop: '2px', flexShrink: 0, color: '#d97706' }} />
            <span>{disclaimer}</span>
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
            <VoicePlayer text={message.content} />
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
