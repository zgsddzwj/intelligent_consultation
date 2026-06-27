import { useState, useEffect } from 'react'
import { Collapse } from 'antd'
import {
  BulbOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import type { ThinkingStep } from '../../types/chat'

interface ThinkingPanelProps {
  steps: ThinkingStep[]
  isThinking?: boolean
}

function ThinkingPanel({ steps, isThinking }: ThinkingPanelProps) {
  // 思考中默认展开，完成后自动折叠
  const [activeKeys, setActiveKeys] = useState<string[]>(['thinking'])

  useEffect(() => {
    if (isThinking) {
      setActiveKeys(['thinking'])
    } else {
      // 思考完成后延迟折叠
      const timer = setTimeout(() => setActiveKeys([]), 800)
      return () => clearTimeout(timer)
    }
  }, [isThinking])

  if (!steps || steps.length === 0) return null

  const header = (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      {isThinking ? (
        <LoadingOutlined style={{ fontSize: '14px', color: 'var(--primary-color)' }} />
      ) : (
        <CheckCircleOutlined style={{ fontSize: '14px', color: '#52c41a' }} />
      )}
      <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)' }}>
        {isThinking ? '思考中...' : `已深度思考（${steps.length}步）`}
      </span>
    </div>
  )

  return (
    <Collapse
      activeKey={activeKeys}
      onChange={(keys) => setActiveKeys(keys as string[])}
      ghost
      size="small"
      style={{
        marginBottom: '4px',
        padding: 0,
        border: 'none',
      }}
      items={[
        {
          key: 'thinking',
          label: header,
          children: (
            <div
              style={{
                padding: '8px 12px',
                background: 'var(--bg-secondary, #f8f9fa)',
                borderRadius: '8px',
                border: '1px solid var(--border-color-light, #f0f0f0)',
                fontSize: '12.5px',
                lineHeight: '1.8',
                color: 'var(--text-secondary, #666)',
              }}
            >
              {steps.map((step, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '6px',
                    marginBottom: i < steps.length - 1 ? '4px' : 0,
                    opacity: isThinking && i === steps.length - 1 ? 1 : 0.75,
                  }}
                >
                  <BulbOutlined
                    style={{
                      fontSize: '12px',
                      marginTop: '3px',
                      color: isThinking && i === steps.length - 1 ? 'var(--primary-color)' : '#999',
                      flexShrink: 0,
                    }}
                  />
                  <span>{step.content}</span>
                </div>
              ))}
            </div>
          ),
        },
      ]}
    />
  )
}

export default ThinkingPanel
