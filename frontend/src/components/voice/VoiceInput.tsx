import { useState, useEffect, useCallback, useRef } from 'react'
import { Button, Tooltip, message } from 'antd'
import { AudioOutlined, LoadingOutlined } from '@ant-design/icons'
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition'

interface VoiceInputProps {
  /** 语音识别结果回调（识别完成后触发） */
  onTranscript: (text: string) => void
  /** 语音识别完成后自动发送（可选） */
  onSend?: (text: string) => void
  /** 是否禁用 */
  disabled?: boolean
  /** 按钮变体：'circle' 圆形(44px) | 'rounded' 圆角方形(56px) */
  variant?: 'circle' | 'rounded'
}

/**
 * 语音输入组件
 *
 * 使用浏览器原生 Web Speech API 进行实时语音识别。
 * 点击按钮开始录音，再次点击停止并自动将识别文本发送。
 *
 * 工作流程：
 * 1. 用户点击麦克风按钮 → 开始实时语音识别
 * 2. 识别过程中显示实时文字反馈
 * 3. 用户再次点击 → 停止识别
 * 4. 自动调用 onSend(text) 发送消息（如果提供了 onSend）
 *    否则调用 onTranscript(text) 填入输入框
 *
 * 支持浏览器：Chrome、Edge、Safari（需联网）
 */
export default function VoiceInput({
  onTranscript,
  onSend,
  disabled = false,
  variant = 'rounded',
}: VoiceInputProps) {
  const isCircle = variant === 'circle'

  // 用 ref 存储回调，避免回调引用变化触发 useEffect 无限循环
  const onTranscriptRef = useRef(onTranscript)
  const onSendRef = useRef(onSend)
  onTranscriptRef.current = onTranscript
  onSendRef.current = onSend

  // 记录识别停止时的最终文本，以及是否已触发发送
  const finalTextRef = useRef('')
  const [autoSendTriggered, setAutoSendTriggered] = useState(false)

  const {
    isListening,
    interimTranscript,
    finalTranscript,
    error,
    isSupported,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechRecognition('zh-CN')

  // 错误提示
  useEffect(() => {
    if (error) {
      message.error(error)
    }
  }, [error])

  // 当识别有最终结果时，实时更新输入框（让用户看到识别进度）
  // 注意：onTranscript 不在依赖数组中，通过 ref 调用，避免无限循环
  useEffect(() => {
    if (finalTranscript) {
      finalTextRef.current = finalTranscript
      onTranscriptRef.current(finalTranscript)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finalTranscript])

  // 识别停止后，如果有文本则自动发送
  useEffect(() => {
    if (!isListening && finalTextRef.current && !autoSendTriggered) {
      const text = finalTextRef.current.trim()
      if (text) {
        setAutoSendTriggered(true)
        if (onSendRef.current) {
          onSendRef.current(text)
        } else {
          onTranscriptRef.current(text)
        }
      }
      // 清理状态
      finalTextRef.current = ''
      resetTranscript()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isListening, autoSendTriggered])

  // hover 样式工具函数
  const getHoverStyle = useCallback((isHover: boolean) => {
    if (isCircle) {
      return {
        background: isHover ? 'rgba(37, 99, 235, 0.12)' : 'var(--primary-50, rgba(37, 99, 235, 0.06))',
        borderColor: isHover ? 'var(--primary-color, #2563eb)' : 'var(--primary-200, rgba(37, 99, 235, 0.2))',
      }
    }
    return {
      background: isHover ? 'rgba(102, 126, 234, 0.2)' : 'rgba(102, 126, 234, 0.1)',
      borderColor: isHover ? '#667eea' : 'rgba(102, 126, 234, 0.2)',
    }
  }, [isCircle])

  const handleClick = useCallback(() => {
    if (!isSupported) {
      message.warning('当前浏览器不支持语音识别，请使用 Chrome、Edge 或 Safari 浏览器')
      return
    }

    if (isListening) {
      stopListening()
    } else {
      setAutoSendTriggered(false)
      finalTextRef.current = ''
      resetTranscript()
      startListening()
    }
  }, [isListening, isSupported, startListening, stopListening, resetTranscript])

  // 按钮样式
  const buttonStyle: React.CSSProperties = {
    borderRadius: isCircle ? '50%' : '12px',
    height: isCircle ? '44px' : '56px',
    width: isCircle ? '44px' : '56px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: isListening
      ? 'rgba(239, 68, 68, 0.12)'
      : isCircle
        ? 'var(--primary-50, rgba(37, 99, 235, 0.06))'
        : 'rgba(102, 126, 234, 0.1)',
    border: isCircle
      ? `1px solid ${isListening ? 'rgba(239, 68, 68, 0.3)' : 'var(--primary-200, rgba(37, 99, 235, 0.2))'}`
      : `2px solid ${isListening ? 'rgba(239, 68, 68, 0.3)' : 'rgba(102, 126, 234, 0.2)'}`,
    color: isListening ? '#ef4444' : isCircle ? 'var(--primary-color, #2563eb)' : '#667eea',
    transition: 'all 0.3s ease',
    ...(isListening
      ? {
          animation: 'voice-pulse 1.5s ease-in-out infinite',
        }
      : {}),
  }

  const tooltipTitle = !isSupported
    ? '当前浏览器不支持语音识别'
    : isListening
      ? interimTranscript
        ? `识别中: ${interimTranscript}`
        : '正在聆听... 点击停止并发送'
      : '语音输入（点击开始说话）'

  return (
    <>
      <Tooltip title={tooltipTitle} open={isListening ? true : undefined}>
        <Button
          type="text"
          icon={isListening ? <LoadingOutlined /> : <AudioOutlined />}
          onClick={handleClick}
          disabled={disabled || !isSupported}
          style={buttonStyle}
          onMouseEnter={(e) => {
            if (!disabled && !isListening) {
              const s = getHoverStyle(true)
              e.currentTarget.style.background = s.background
              e.currentTarget.style.borderColor = s.borderColor
            }
          }}
          onMouseLeave={(e) => {
            if (!disabled && !isListening) {
              const s = getHoverStyle(false)
              e.currentTarget.style.background = s.background
              e.currentTarget.style.borderColor = s.borderColor
            }
          }}
        />
      </Tooltip>

      {/* 录音中的浮动提示条 */}
      {isListening && (
        <div
          style={{
            position: 'fixed',
            bottom: '120px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(0, 0, 0, 0.75)',
            color: '#fff',
            padding: '8px 20px',
            borderRadius: '20px',
            fontSize: '14px',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            maxWidth: '80vw',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#ef4444',
              animation: 'voice-dot 1s ease-in-out infinite',
              flexShrink: 0,
            }}
          />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {interimTranscript || '正在聆听...'}
          </span>
        </div>
      )}

      <style>{`
        @keyframes voice-pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.08); }
        }
        @keyframes voice-dot {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </>
  )
}
