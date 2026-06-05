import { useState, useRef, useEffect } from 'react'
import { Layout, Input, Button, message, Upload, Tag, Space, Tooltip, Badge, Typography } from 'antd'
import {
  SendOutlined,
  MedicineBoxOutlined,
  HeartOutlined,
  BulbOutlined,
  SafetyCertificateOutlined,
  FileImageOutlined,
} from '@ant-design/icons'
import { ChatMessage, TypingIndicator, WelcomeScreen } from '../components/chat'
import { useMutation } from '@tanstack/react-query'
import { consultationApi } from '../services/consultation'
import { useConsultationStore } from '../stores/consultation'
import { post, ApiError } from '../services/api'
import { getAuthUser } from '../services/auth'
import type { ChatRequest, Message } from '../types/chat'

const { Header, Content } = Layout
const { TextArea } = Input
const { Text, Title } = Typography

// 快捷问题建议
const quickSuggestions = [
  { icon: <HeartOutlined />, text: '头痛怎么办', color: '#ff4d4f' },
  { icon: <BulbOutlined />, text: '感冒用药建议', color: '#faad14' },
  { icon: <MedicineBoxOutlined />, text: '血压正常范围', color: '#52c41a' },
  { icon: <SafetyCertificateOutlined />, text: '体检报告解读', color: '#1890ff' },
]

export default function PatientPortal() {
  const messages = useConsultationStore((state) => state.messages)
  const consultationId = useConsultationStore((state) => state.consultationId)
  const addMessage = useConsultationStore((state) => state.addMessage)
  const setConsultationId = useConsultationStore((state) => state.setConsultationId)

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

  const buildChatRequest = (message: string): ChatRequest => {
    const authUser = getAuthUser()
    return {
      message,
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

      const analysisText = `📸 图片分析结果：\n${response.analysis_result}\n\n🔍 提取的医疗术语：${JSON.stringify(response.medical_terms, null, 2)}`
      
      addMessage({ role: 'user', content: `🖼️ [图片] ${file.name}` })
      addMessage({ role: 'assistant', content: analysisText })
      
      message.success('图片分析完成')
    } catch (error: unknown) {
      const msg = error instanceof ApiError ? error.message : (error instanceof Error ? error.message : '未知错误')
      message.error('图片分析失败: ' + msg)
    }
    return false
  }

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--background-light)' }}>
      {/* 页面头部 */}
      <Header style={{
        background: 'var(--background-white)',
        padding: '0 32px',
        borderBottom: '1px solid var(--border-color)',
        boxShadow: 'var(--shadow-xs)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '72px',
        lineHeight: '72px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '14px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(102, 126, 234, 0.3)',
          }}>
            <MedicineBoxOutlined style={{ fontSize: '22px', color: 'white' }} />
          </div>
          <div>
            <Title level={4} style={{ margin: 0, fontWeight: 700, lineHeight: 1.3, fontSize: '17px' }}>
              患者咨询门户
            </Title>
            <Text type="secondary" style={{ fontSize: '12px' }}>AI驱动的智能问诊助手</Text>
          </div>
        </div>

        <Space size="small">
          <Badge status="success" />
          <Tag color="blue" style={{ borderRadius: '20px', padding: '4px 14px', fontWeight: 500 }}>
            在线服务中
          </Tag>
        </Space>
      </Header>

      {/* 主内容区 */}
      <Content style={{
        padding: '24px 32px',
        maxWidth: '1200px',
        margin: '0 auto',
        width: '100%',
        minHeight: 'calc(100vh - 72px - 56px)',
      }}>
        {/* 聊天容器 */}
        <div
          style={{
            height: 'calc(100vh - 200px)',
            minHeight: '500px',
            display: 'flex',
            flexDirection: 'column',
            borderRadius: '24px',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-lg)',
            background: 'var(--background-white)',
            border: '1px solid var(--border-color)',
          }}
        >
          {/* 消息列表区域 */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px 0',
            position: 'relative',
          }}>
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
          <div style={{
            padding: '20px 24px',
            background: 'var(--background-warm)',
            borderTop: '1px solid var(--border-color)',
          }}>
            <div style={{
              display: 'flex',
              gap: '14px',
              alignItems: 'flex-end',
            }}>
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
                  placeholder="描述您的症状或健康问题，AI将为您提供专业建议..."
                  rows={2}
                  disabled={chatMutation.isPending}
                  style={{
                    borderRadius: '16px',
                    border: '1.5px solid var(--border-color-strong)',
                    fontSize: '15px',
                    resize: 'none',
                    transition: 'all 0.3s ease',
                    background: 'var(--background-white)',
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = 'var(--primary-color)'
                    e.target.style.boxShadow = '0 0 0 4px rgba(102, 126, 234, 0.08)'
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'var(--border-color-strong)'
                    e.target.style.boxShadow = 'none'
                  }}
                />
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: '8px',
                }}>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    ⌨️ Enter 发送 · Shift+Enter 换行
                  </Text>
                  {input.length > 0 && (
                    <Text style={{ fontSize: '12px', color: 'var(--primary-color)', fontWeight: 600 }}>
                      {input.length} 字符
                    </Text>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
                <Tooltip title="上传图片进行医疗识别">
                  <Upload beforeUpload={handleImageUpload} showUploadList={false} accept="image/*">
                    <Button
                      icon={<FileImageOutlined />}
                      shape="circle"
                      size="large"
                      style={{
                        width: '48px',
                        height: '48px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderColor: 'var(--primary-200)',
                        color: 'var(--primary-color)',
                        background: 'var(--primary-50)',
                        transition: 'all 0.3s ease',
                      }}
                    />
                  </Upload>
                </Tooltip>

                <Tooltip title="发送消息">
                  <Button
                    type="primary"
                    shape="circle"
                    size="large"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    loading={chatMutation.isPending}
                    disabled={!input.trim()}
                    style={{
                      width: '48px',
                      height: '48px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      opacity: !input.trim() || chatMutation.isPending ? 0.5 : 1,
                      transform: !input.trim() || chatMutation.isPending ? 'none' : undefined,
                    }}
                  />
                </Tooltip>
              </div>
            </div>
          </div>
        </div>
      </Content>
    </Layout>
  )
}
