import { useState, useRef, useEffect } from 'react'
import { Layout, Input, Button, message, Upload, Avatar, Tag, Spin, Space, Tooltip, Badge, Typography, Card } from 'antd'
import {
  SendOutlined,
  UploadOutlined,
  UserOutlined,
  RobotOutlined,
  MedicineBoxOutlined,
  HeartOutlined,
  BulbOutlined,
  SafetyCertificateOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  FileImageOutlined,
} from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import { consultationApi, ChatRequest } from '../services/consultation'
import { useConsultationStore } from '../stores/consultation'
import api from '../services/api'

const { Header, Content } = Layout
const { TextArea } = Input
const { Text, Title, Paragraph } = Typography

// 快捷问题建议
const quickSuggestions = [
  { icon: <HeartOutlined />, text: '头痛怎么办', color: '#ff4d4f' },
  { icon: <BulbOutlined />, text: '感冒用药建议', color: '#faad14' },
  { icon: <MedicineBoxOutlined />, text: '血压正常范围', color: '#52c41a' },
  { icon: <SafetyCertificateOutlined />, text: '体检报告解读', color: '#1890ff' },
]

// 功能特性
const features = [
  { icon: <ThunderboltOutlined />, title: '秒级响应', desc: 'AI智能快速分析', color: '#667eea' },
  { icon: <SafetyCertificateOutlined />, title: '专业可靠', desc: '基于医学知识库', color: '#10b981' },
  { icon: <ClockCircleOutlined />, title: '24小时在线', desc: '随时健康咨询', color: '#f59e0b' },
]

export default function PatientPortal() {
  const [input, setInput] = useState('')
  const { messages, consultationId, addMessage, setConsultationId } = useConsultationStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [isTyping, setIsTyping] = useState(false)

  const chatMutation = useMutation({
    mutationFn: (data: ChatRequest) => consultationApi.chat(data),
    onSuccess: (data) => {
      setIsTyping(false)
      addMessage({
        role: 'assistant',
        content: data.data.answer,
        sources: data.data.sources,
        risk_level: data.data.risk_level,
      })
      if (data.data.consultation_id) {
        setConsultationId(data.data.consultation_id)
      }
      setInput('')
    },
    onError: (error: any) => {
      setIsTyping(false)
      message.error('发送消息失败: ' + (error.response?.data?.error?.message || error.message || '未知错误'))
    },
  })

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSend = () => {
    if (!input.trim() || chatMutation.isPending) return

    const userMessage = input.trim()
    addMessage({ role: 'user', content: userMessage })
    setInput('')
    setIsTyping(true)

    chatMutation.mutate({
      message: userMessage,
      consultation_id: consultationId || undefined,
    })
  }

  const handleQuickSuggestion = (text: string) => {
    setInput(text)
    // 自动发送快捷问题
    setTimeout(() => {
      addMessage({ role: 'user', content: text })
      setIsTyping(true)
      chatMutation.mutate({
        message: text,
        consultation_id: consultationId || undefined,
      })
    }, 100)
  }

  const handleImageUpload = async (file: File) => {
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await api.post('/image_analysis/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      
      const analysisText = `📸 图片分析结果：\n${response.data.analysis_result}\n\n🔍 提取的医疗术语：${JSON.stringify(response.data.medical_terms, null, 2)}`
      
      addMessage({ role: 'user', content: `🖼️ [图片] ${file.name}` })
      addMessage({ role: 'assistant', content: analysisText })
      
      message.success('图片分析完成')
    } catch (error: any) {
      message.error('图片分析失败: ' + (error.response?.data?.error?.message || error.message || '未知错误'))
    }
    return false
  }

  // 风险等级配置
  const getRiskConfig = (level?: string) => {
    switch (level) {
      case 'high':
        return { bg: '#fff2f0', border: '#ffccc7', color: '#cf1322', label: '高风险', icon: '🚨' }
      case 'medium':
        return { bg: '#fffbe6', border: '#ffe58f', color: '#d48806', label: '中等风险', icon: '⚠️' }
      case 'low':
        return { bg: '#f6ffed', border: '#d9f7be', color: '#389e0d', label: '低风险', icon: '✅' }
      default:
        return null
    }
  }

  // 渲染单条消息
  const renderMessage = (item: any, index: number) => {
    const isUser = item.role === 'user'

    return (
      <div
        key={index}
        className="animate-fade-in"
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: '20px',
          alignItems: 'flex-start',
          gap: '12px',
          padding: '0 20px',
        }}
      >
        {/* AI头像 */}
        {!isUser && (
          <Avatar
            icon={<RobotOutlined />}
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              flexShrink: 0,
              boxShadow: '0 4px 16px rgba(102, 126, 234, 0.35)',
            }}
            size={40}
          />
        )}

        {/* 消息气泡 */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: isUser ? 'flex-end' : 'flex-start',
            maxWidth: '68%',
          }}
        >
          <div
            style={{
              padding: '16px 22px',
              borderRadius: isUser ? '20px 20px 6px 20px' : '20px 20px 20px 6px',
              background: isUser
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                : '#ffffff',
              color: isUser ? '#fff' : 'var(--text-primary)',
              boxShadow: isUser
                ? '0 4px 24px rgba(102, 126, 234, 0.4)'
                : '0 2px 12px rgba(0, 0, 0, 0.06)',
              border: isUser ? 'none' : '1px solid var(--border-color)',
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
              fontSize: '15px',
              lineHeight: '1.7',
              position: 'relative',
            }}
          >
            {item.content}

            {/* 信息来源 */}
            {item.sources && item.sources.length > 0 && (
              <div style={{
                marginTop: '12px',
                paddingTop: '10px',
                borderTop: `1px solid ${isUser ? 'rgba(255,255,255,0.25)' : 'var(--border-color)'}`,
                fontSize: '12px',
                opacity: 0.85,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}>
                <span>📚</span>
                <Text style={{ fontSize: '12px', color: isUser ? 'rgba(255,255,255,0.85)' : 'var(--text-hint)' }}>
                  来源: {item.sources.join(', ')}
                </Text>
              </div>
            )}

            {/* 风险标签 */}
            {item.risk_level && (() => {
              const config = getRiskConfig(item.risk_level)
              if (!config) return null
              return (
                <div style={{
                  marginTop: '10px',
                  padding: '5px 12px',
                  borderRadius: '20px',
                  background: config.bg,
                  border: `1px solid ${config.border}`,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}>
                  <span>{config.icon}</span>
                  <Text style={{ fontSize: '12px', fontWeight: 600, color: config.color }}>
                    {config.label}
                  </Text>
                </div>
              )
            })()}
          </div>

          {/* 时间戳 */}
          <Text
            type="secondary"
            style={{ fontSize: '11px', marginTop: '6px', padding: '0 4px' }}
          >
            {item.timestamp ? new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}
          </Text>
        </div>

        {/* 用户头像 */}
        {isUser && (
          <Avatar
            icon={<UserOutlined />}
            style={{
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              flexShrink: 0,
              boxShadow: '0 4px 16px rgba(16, 185, 129, 0.3)',
            }}
            size={40}
          />
        )}
      </div>
    )
  }

  // 打字指示器组件
  const TypingIndicator = () => (
    <div style={{
      display: 'flex',
      gap: '12px',
      marginTop: '20px',
      padding: '0 20px',
      animation: 'fadeIn 0.3s ease-out',
    }}>
      <Avatar
        icon={<RobotOutlined />}
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          boxShadow: '0 4px 16px rgba(102, 126, 234, 0.3)',
        }}
        size={40}
      />
      <div style={{
        padding: '18px 24px',
        borderRadius: '20px 20px 20px 6px',
        background: '#ffffff',
        boxShadow: '0 2px 12px rgba(0, 0, 0, 0.06)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        border: '1px solid var(--border-color)',
      }}>
        <div style={{ display: 'flex', gap: '5px' }}>
          {[0, 1, 2].map((i) => (
            <div key={i} style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#667eea',
              animation: 'typingDot 1.4s ease-in-out infinite',
              animationDelay: `${i * 0.2}s`,
            }} />
          ))}
        </div>
        <Text type="secondary" style={{ fontSize: '14px', marginLeft: '4px' }}>
          AI 正在思考中...
        </Text>
      </div>
    </div>
  )

  // 空状态欢迎页面
  const WelcomeScreen = () => (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      padding: '40px',
      animation: 'fadeInUp 0.6s ease-out',
    }}>
      {/* Logo动画区域 */}
      <div style={{
        width: '110px',
        height: '110px',
        borderRadius: '32px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: '28px',
        boxShadow: '0 12px 40px rgba(102, 126, 234, 0.35)',
        position: 'relative',
      }}>
        <MedicineBoxOutlined style={{ fontSize: '46px', color: 'white' }} />
        {/* 脉冲环效果 */}
        <div style={{
          position: 'absolute',
          inset: '-8px',
          borderRadius: '36px',
          border: '2px solid rgba(102, 126, 234, 0.3)',
          animation: 'pulse 2.5s ease-in-out infinite',
        }} />
      </div>

      <Title level={2} style={{
        color: 'var(--text-primary)',
        fontWeight: 700,
        marginBottom: '10px',
        textAlign: 'center',
        letterSpacing: '-0.02em',
      }}>
        欢迎使用智能医疗管家
      </Title>

      <Paragraph style={{
        color: 'var(--text-secondary)',
        fontSize: '15px',
        textAlign: 'center',
        lineHeight: '1.7',
        marginBottom: '32px',
        maxWidth: '480px',
      }}>
        我是您的AI医疗助手，基于专业医学知识库，为您提供精准的健康咨询、用药指导和症状分析服务。
      </Paragraph>

      {/* 快捷问题 */}
      <div style={{ marginBottom: '28px', width: '100%', maxWidth: '520px' }}>
        <Text type="secondary" style={{ fontSize: '13px', display: 'block', marginBottom: '14px', textAlign: 'center' }}>
          💡 常见问题快捷入口
        </Text>
        <Space wrap size="middle" justify="center" style={{ width: '100%' }}>
          {quickSuggestions.map((item, idx) => (
            <div
              key={idx}
              onClick={() => handleQuickSuggestion(item.text)}
              style={{
                cursor: 'pointer',
                padding: '12px 20px',
                borderRadius: '16px',
                background: 'var(--background-white)',
                border: '1px solid var(--border-color)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                textAlign: 'center',
                minWidth: '120px',
                animationDelay: `${idx * 100}ms`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = item.color
                e.currentTarget.style.boxShadow = `0 4px 16px ${item.color}20`
                e.currentTarget.style.transform = 'translateY(-2px)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)'
                e.currentTarget.style.boxShadow = 'none'
                e.currentTarget.style.transform = 'translateY(0)'
              }}
            >
              <div style={{ fontSize: '24px', marginBottom: '6px', color: item.color }}>{item.icon}</div>
              <Text style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>{item.text}</Text>
            </div>
          ))}
        </Space>
      </div>

      {/* 特性卡片 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '16px',
        width: '100%',
        maxWidth: '520px',
      }}>
        {features.map((feat, idx) => (
          <div
            key={idx}
            style={{
              padding: '18px 16px',
              borderRadius: '16px',
              background: `${feat.color}08`,
              border: `1px solid ${feat.color}20`,
              textAlign: 'center',
              transition: 'all 0.3s ease',
            }}
          >
            <div style={{ fontSize: '26px', marginBottom: '8px', color: feat.color }}>{feat.icon}</div>
            <Text strong style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>
              {feat.title}
            </Text>
            <Text type="secondary" style={{ fontSize: '11px' }}>{feat.desc}</Text>
          </div>
        ))}
      </div>

      {/* 免责声明 */}
      <div style={{
        marginTop: '28px',
        padding: '14px 24px',
        borderRadius: '14px',
        background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.06), rgba(118, 75, 162, 0.06))',
        border: '1px solid rgba(102, 126, 234, 0.12)',
        maxWidth: '520px',
        width: '100%',
      }}>
        <Text type="secondary" style={{ fontSize: '13px', lineHeight: 1.7, textAlign: 'center', display: 'block' }}>
          ⚕️ <strong>温馨提示：</strong>本平台提供的医疗信息仅供参考，不替代专业医生的诊断和治疗。如有紧急情况，请立即拨打急救电话或前往医院就诊。
        </Text>
      </div>
    </div>
  )

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
              <WelcomeScreen />
            ) : (
              <>
                {messages.map(renderMessage)}
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
