import { useRef, useEffect, useCallback, useState } from 'react'
import { Layout, message, Tag, Space } from 'antd'
import { MedicineBoxOutlined } from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import { consultationApi } from '../services/consultation'
import { useConsultationStore } from '../stores/consultation'
import api from '../services/api'
import {
  ChatMessage,
  ChatInput,
  WelcomeScreen,
  TypingIndicator,
} from '../components/chat'
import type { ChatRequest, ImageAnalysisResponse } from '../types/chat'

const { Header, Content } = Layout

export default function PatientPortal() {
  const messages = useConsultationStore((state) => state.messages)
  const consultationId = useConsultationStore((state) => state.consultationId)
  const addMessage = useConsultationStore((state) => state.addMessage)
  const setConsultationId = useConsultationStore((state) => state.setConsultationId)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [isTyping, setIsTyping] = useState(false)

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  // 聊天请求
  const chatMutation = useMutation({
    mutationFn: (data: ChatRequest) => consultationApi.chat(data),
    onSuccess: (response) => {
      setIsTyping(false)
      const data = response.data
      addMessage({
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        risk_level: data.risk_level,
      })
      if (data.consultation_id) {
        setConsultationId(data.consultation_id)
      }
    },
    onError: (error: any) => {
      setIsTyping(false)
      message.error(
        '发送消息失败: ' + (error.message || '未知错误')
      )
    },
  })

  const handleSend = useCallback(
    (text: string) => {
      if (!text.trim() || chatMutation.isPending) return

      addMessage({
        role: 'user',
        content: text.trim(),
      })
      setIsTyping(true)

      chatMutation.mutate({
        message: text.trim(),
        consultation_id: consultationId || undefined,
      })
    },
    [addMessage, chatMutation, consultationId]
  )

  const handleImageUpload = useCallback(
    async (file: File) => {
      try {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post<ImageAnalysisResponse>(
          '/image_analysis/analyze',
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        )

        const data = response as unknown as ImageAnalysisResponse
        const analysisText = `📸 图片分析结果：\n${data.analysis_result}\n\n🔍 提取的医疗术语：${JSON.stringify(data.medical_terms, null, 2)}`

        addMessage({
          role: 'user',
          content: `🖼️ [图片] ${file.name}`,
        })

        addMessage({
          role: 'assistant',
          content: analysisText,
        })

        message.success('图片分析完成')
      } catch (error: any) {
        message.error(
          '图片分析失败: ' + (error.message || '未知错误')
        )
      }
    },
    [addMessage]
  )

  return (
    <Layout
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        position: 'relative',
      }}
    >
      {/* 背景装饰 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: `
            radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 40% 80%, rgba(120, 219, 226, 0.3) 0%, transparent 50%)
          `,
          pointerEvents: 'none',
        }}
      />

      {/* 顶部导航栏 */}
      <Header
        style={{
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(20px)',
          padding: '12px 32px',
          borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'relative',
          zIndex: 10,
          height: 'auto',
          minHeight: '80px',
          lineHeight: 'normal',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            flex: 1,
            minWidth: 0,
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 16px rgba(102, 126, 234, 0.3)',
              flexShrink: 0,
            }}
          >
            <MedicineBoxOutlined style={{ fontSize: '24px', color: 'white' }} />
          </div>
          <div style={{ flex: 1, minWidth: 0, overflow: 'visible' }}>
            <h1
              style={{
                margin: 0,
                color: '#333',
                fontWeight: '700',
                fontSize: '20px',
                lineHeight: '28px',
                wordBreak: 'keep-all',
                whiteSpace: 'normal',
              }}
            >
              智能医疗管家平台
            </h1>
            <p
              style={{
                margin: '4px 0 0 0',
                color: '#666',
                fontSize: '14px',
                opacity: 0.8,
                lineHeight: '20px',
                wordBreak: 'keep-all',
                whiteSpace: 'normal',
              }}
            >
              专业的AI医疗咨询助手
            </p>
          </div>
        </div>

        <Space style={{ flexShrink: 0, marginLeft: '16px' }}>
          <Tag
            color="blue"
            style={{ fontSize: '13px', padding: '4px 12px', borderRadius: '16px' }}
          >
            🏥 患者端
          </Tag>
          <Tag
            color="green"
            style={{ fontSize: '13px', padding: '4px 12px', borderRadius: '16px' }}
          >
            🔒 安全可靠
          </Tag>
        </Space>
      </Header>

      {/* 内容区域 */}
      <Content
        style={{
          padding: '32px',
          maxWidth: '1400px',
          margin: '0 auto',
          width: '100%',
          minHeight: 'calc(100vh - 80px)',
          position: 'relative',
          zIndex: 5,
        }}
      >
        <div
          style={{
            height: 'calc(100vh - 196px)',
            display: 'flex',
            flexDirection: 'column',
            borderRadius: '24px',
            overflow: 'hidden',
            boxShadow: '0 16px 48px rgba(0, 0, 0, 0.15)',
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
          }}
        >
          {/* 消息区域 */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '24px 0',
              position: 'relative',
            }}
          >
            {messages.length === 0 ? (
              <WelcomeScreen />
            ) : (
              <>
                {messages.map((msg, index) => (
                  <ChatMessage key={index} message={msg} index={index} />
                ))}
                {isTyping && <TypingIndicator />}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <ChatInput
            onSend={handleSend}
            onImageUpload={handleImageUpload}
            loading={chatMutation.isPending}
          />
        </div>
      </Content>
    </Layout>
  )
}
