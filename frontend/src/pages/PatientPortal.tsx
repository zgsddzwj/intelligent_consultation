import { useState, useRef, useEffect } from 'react'
import { Input, Button, message, Upload, Tag, Tooltip, Badge, Typography, Space } from 'antd'
import {
  SendOutlined,
  MedicineBoxOutlined,
  HeartOutlined,
  BulbOutlined,
  SafetyCertificateOutlined,
  FileImageOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { ChatMessage, TypingIndicator, WelcomeScreen } from '../components/chat'
import { useMutation } from '@tanstack/react-query'
import { consultationApi } from '../services/consultation'
import { useConsultationStore } from '../stores/consultation'
import { post, ApiError } from '../services/api'
import { getAuthUser } from '../services/auth'
import type { ChatRequest, Message } from '../types/chat'

const { TextArea } = Input
const { Text } = Typography

// 快捷问题建议
const quickSuggestions = [
  { icon: <HeartOutlined />, text: '头痛怎么办', color: '#dc2626' },
  { icon: <BulbOutlined />, text: '感冒用药建议', color: '#d97706' },
  { icon: <MedicineBoxOutlined />, text: '血压正常范围', color: '#16a34a' },
  { icon: <SafetyCertificateOutlined />, text: '体检报告解读', color: '#2563eb' },
]

export default function PatientPortal() {
  const messages = useConsultationStore((state) => state.messages)
  const consultationId = useConsultationStore((state) => state.consultationId)
  const addMessage = useConsultationStore((state) => state.addMessage)
  const setConsultationId = useConsultationStore((state) => state.setConsultationId)
  const clearMessages = useConsultationStore((state) => state.clearMessages)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [isTyping, setIsTyping] = useState(false)
  const [input, setInput] = useState('')

  const chatMutation = useMutation({
    mutationFn: (req: ChatRequest) => consultationApi.chat(req),
    onSuccess: (data) => {
      addMessage({
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        risk_level: data.risk_level,
      })
      if (data.consultation_id) {
        setConsultationId(data.consultation_id)
      }
      setIsTyping(false)
    },
    onError: (error: Error) => {
      message.error('发送失败: ' + (error.message || '请稍后重试'))
      setIsTyping(false)
    },
  })

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const buildChatRequest = (msg: string): ChatRequest => {
    const authUser = getAuthUser()
    return {
      message: msg,
      consultation_id: consultationId || undefined,
      user_id: authUser?.id,
    }
  }

  const handleSend = () => {
    if (!input.trim() || chatMutation.isPending) return

    const userMessage = input.trim()
    addMessage({ role: 'user', content: userMessage })
    setInput('')
    setIsTyping(true)

    chatMutation.mutate(buildChatRequest(userMessage))
  }

  const handleQuickSuggestion = (text: string) => {
    addMessage({ role: 'user', content: text })
    setIsTyping(true)
    chatMutation.mutate(buildChatRequest(text))
  }

  const handleImageUpload = async (file: File) => {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await post<{ analysis_result: string; medical_terms: string[] }>(
        '/image_analysis/analyze',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )

      const analysisText = `图片分析结果：\n${response.analysis_result}\n\n提取的医疗术语：${JSON.stringify(response.medical_terms, null, 2)}`

      addMessage({ role: 'user', content: `[图片] ${file.name}` })
      addMessage({ role: 'assistant', content: analysisText })

      message.success('图片分析完成')
    } catch (error: unknown) {
      const msg = error instanceof ApiError ? error.message : (error instanceof Error ? error.message : '未知错误')
      message.error('图片分析失败: ' + msg)
    }
    return false
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* 页面标题栏 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 32px',
          background: 'var(--background-white)',
          borderBottom: '1px solid var(--border-color)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <MedicineBoxOutlined style={{ fontSize: '20px', color: '#fff' }} />
          </div>
          <div>
            <Text strong style={{ fontSize: '16px' }}>患者咨询门户</Text>
            <br />
            <Text type="secondary" style={{ fontSize: '12px' }}>AI 驱动的智能问诊助手</Text>
          </div>
        </div>

        <Space size="middle">
          <Badge status="success" />
          <Tag color="blue" style={{ margin: 0 }}>在线服务中</Tag>
          {messages.length > 0 && (
            <Tooltip title="清空对话">
              <Button
                type="text"
                icon={<DeleteOutlined />}
                onClick={() => {
                  clearMessages()
                  message.success('对话已清空')
                }}
                size="small"
              />
            </Tooltip>
          )}
        </Space>
      </div>

      {/* 聊天容器 */}
        <div
          style={{
            flex: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            maxWidth: '960px',
            width: '100%',
            margin: '0 auto',
          }}
>
        {/* 消息列表 */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px 0',
          }}
        >
          {messages.length === 0 ? (
            <WelcomeScreen
              quickSuggestions={quickSuggestions}
              onQuickSuggestion={handleQuickSuggestion}
            />
          ) : (
            <>
              {messages.map((item, index) => (
                <ChatMessage
                  key={item.id || index}
                  message={{ ...item, id: item.id || String(index) } as Message}
                  index={index}
                />
              ))}
              {isTyping && <TypingIndicator />}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div
          style={{
            padding: '16px 24px 20px',
            background: 'var(--background-white)',
            borderTop: '1px solid var(--border-color)',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <TextArea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                placeholder="描述您的症状或健康问题，AI 将为您提供专业建议..."
                rows={2}
                disabled={chatMutation.isPending}
                style={{
                  borderRadius: '12px',
                  fontSize: '14px',
                  resize: 'none',
                  transition: 'all 0.25s ease',
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--primary-color)'
                  e.target.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.08)'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'var(--border-color-strong)'
                  e.target.style.boxShadow = 'none'
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Tooltip title="上传图片进行医疗识别">
                <Upload beforeUpload={handleImageUpload} showUploadList={false} accept="image/*">
                  <Button
                    icon={<FileImageOutlined />}
                    shape="circle"
                    size="large"
                    style={{
                      width: '44px',
                      height: '44px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderColor: 'var(--primary-200)',
                      color: 'var(--primary-color)',
                      background: 'var(--primary-50)',
                    }}
                  />
                </Upload>
              </Tooltip>

              <Tooltip title="发送消息 (Enter)">
                <Button
                  type="primary"
                  shape="circle"
                  size="large"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  loading={chatMutation.isPending}
                  disabled={!input.trim()}
                  style={{
                    width: '44px',
                    height: '44px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                />
              </Tooltip>
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '6px',
              padding: '0 4px',
            }}
          >
            <Text type="secondary" style={{ fontSize: '11px' }}>
              Enter 发送 · Shift+Enter 换行
            </Text>
            {input.length > 0 && (
              <Text style={{ fontSize: '11px', color: 'var(--primary-color)', fontWeight: 600 }}>
                {input.length} 字符
              </Text>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
