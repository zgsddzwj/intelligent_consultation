import { useState, useCallback } from 'react'
import { Input, Button, Upload, Tooltip } from 'antd'
import { SendOutlined, UploadOutlined } from '@ant-design/icons'

const { TextArea } = Input

/** 最大输入长度 */
const MAX_INPUT_LENGTH = 2000
/** 图片文件大小限制：5MB */
const MAX_IMAGE_SIZE = 5 * 1024 * 1024
/** 允许的图片类型 */
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

interface ChatInputProps {
  onSend: (message: string) => void
  onImageUpload: (file: File) => Promise<void> | void
  loading?: boolean
}

export default function ChatInput({ onSend, onImageUpload, loading = false }: ChatInputProps) {
  const [input, setInput] = useState('')

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || loading) return
    onSend(trimmed)
    setInput('')
  }, [input, loading, onSend])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (!e.shiftKey && e.key === 'Enter') {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  const handleBeforeUpload = useCallback(
    (file: File) => {
      // 图片类型校验
      if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
        // 通过 antd Upload 的错误提示
        return Upload.LIST_IGNORE
      }
      // 图片大小校验
      if (file.size > MAX_IMAGE_SIZE) {
        return Upload.LIST_IGNORE
      }
      onImageUpload(file)
      return false // 阻止默认上传行为，手动处理
    },
    [onImageUpload]
  )

  return (
    <div
      style={{
        padding: '24px',
        background: 'rgba(248, 248, 248, 0.8)',
        borderTop: '1px solid rgba(0, 0, 0, 0.06)',
        backdropFilter: 'blur(10px)',
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: '16px',
          alignItems: 'flex-end',
          maxWidth: '100%',
        }}
      >
        {/* 输入框区域 */}
        <div style={{ flex: 1 }}>
          <TextArea
            value={input}
            onChange={(e) => {
              const val = e.target.value
              if (val.length <= MAX_INPUT_LENGTH) {
                setInput(val)
              }
            }}
            onKeyDown={handleKeyDown}
            placeholder="请描述您的症状或健康问题，我会为您提供专业的医疗建议..."
            rows={3}
            disabled={loading}
            maxLength={MAX_INPUT_LENGTH}
            showCount
            style={{
              borderRadius: '16px',
              border: '2px solid rgba(102, 126, 234, 0.2)',
              fontSize: '15px',
              resize: 'none',
              transition: 'all 0.3s ease',
              background: 'rgba(255, 255, 255, 0.9)',
              backdropFilter: 'blur(10px)',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#667eea'
              e.target.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.1)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'rgba(102, 126, 234, 0.2)'
              e.target.style.boxShadow = 'none'
            }}
          />
          <div
            style={{
              fontSize: '12px',
              color: '#999',
              marginTop: '8px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>💡 按 Enter 发送消息，Shift + Enter 换行</span>
          </div>
        </div>

        {/* 操作按钮 */}
        <div style={{ display: 'flex', gap: '12px' }}>
          {/* 图片上传 */}
          <Tooltip title="上传图片进行医疗术语识别（支持 JPG/PNG/GIF/WebP，最大5MB）">
            <Upload
              beforeUpload={handleBeforeUpload}
              showUploadList={false}
              accept="image/jpeg,image/png,image/gif,image/webp"
            >
              <Button
                icon={<UploadOutlined />}
                style={{
                  borderRadius: '12px',
                  height: '56px',
                  width: '56px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(102, 126, 234, 0.1)',
                  border: '2px solid rgba(102, 126, 234, 0.2)',
                  color: '#667eea',
                  transition: 'all 0.3s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(102, 126, 234, 0.2)'
                  e.currentTarget.style.borderColor = '#667eea'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(102, 126, 234, 0.1)'
                  e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.2)'
                }}
              />
            </Upload>
          </Tooltip>

          {/* 发送按钮 */}
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={!input.trim()}
            style={{
              borderRadius: '12px',
              height: '56px',
              width: '80px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background:
                !input.trim() || loading
                  ? '#d9d9d9'
                  : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              border: 'none',
              boxShadow:
                !input.trim() || loading
                  ? 'none'
                  : '0 4px 16px rgba(102, 126, 234, 0.3)',
              transition: 'all 0.3s ease',
            }}
          >
            {!loading && <SendOutlined />}
          </Button>
        </div>
      </div>
    </div>
  )
}
