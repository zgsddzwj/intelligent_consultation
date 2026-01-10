import { useState, useRef, useEffect } from 'react'
import { Layout, Input, Button, message, Upload, Avatar, Tag, Spin, Space, Tooltip } from 'antd'
import { SendOutlined, UploadOutlined, UserOutlined, RobotOutlined, MedicineBoxOutlined, HeartOutlined, BulbOutlined } from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import { consultationApi, ChatRequest } from '../services/consultation'
import { useConsultationStore } from '../stores/consultation'
import api from '../services/api'

const { Header, Content } = Layout
const { TextArea } = Input

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
    addMessage({
      role: 'user',
      content: userMessage,
    })
    setInput('')
    setIsTyping(true)

    chatMutation.mutate({
      message: userMessage,
      consultation_id: consultationId || undefined,
    })
  }

  const handleImageUpload = async (file: File) => {
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await api.post('/image_analysis/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      
      // 将图片分析结果作为消息发送
      const analysisText = `📸 图片分析结果：\n${response.data.analysis_result}\n\n🔍 提取的医疗术语：${JSON.stringify(response.data.medical_terms, null, 2)}`
      
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
      message.error('图片分析失败: ' + (error.response?.data?.error?.message || error.message || '未知错误'))
    }
    return false // 阻止默认上传
  }

  const renderMessage = (item: any, index: number) => {
    const isUser = item.role === 'user'

  return (
      <div
        key={index}
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: '20px',
          alignItems: 'flex-start',
          gap: '12px',
          padding: '0 16px'
        }}
      >
        {!isUser && (
          <Avatar
            icon={<RobotOutlined />}
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              flexShrink: 0,
              boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)'
            }}
            size={40}
          />
        )}

                  <div
                    style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: isUser ? 'flex-end' : 'flex-start',
            maxWidth: '70%'
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
              lineHeight: '1.6'
                      }}
                    >
                      {item.content}

            {/* 附加信息 */}
                      {item.sources && item.sources.length > 0 && (
              <div style={{
                marginTop: '12px',
                paddingTop: '8px',
                borderTop: `1px solid ${isUser ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'}`,
                fontSize: '12px',
                opacity: 0.8
              }}>
                📚 <strong>信息来源:</strong> {item.sources.join(', ')}
                        </div>
                      )}

                      {item.risk_level && (
              <div style={{
                marginTop: '8px',
                padding: '4px 8px',
                borderRadius: '12px',
                background: '#ff4d4f',
                color: 'white',
                fontSize: '11px',
                display: 'inline-block',
                fontWeight: 'bold'
              }}>
                ⚠️ {item.risk_level === 'high' ? '高风险' : item.risk_level === 'medium' ? '中等风险' : '低风险'}
                        </div>
                      )}
          </div>
        </div>

        {isUser && (
          <Avatar
            icon={<UserOutlined />}
            style={{
              background: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)',
              flexShrink: 0,
              boxShadow: '0 4px 12px rgba(82, 196, 26, 0.3)'
            }}
            size={40}
          />
        )}
      </div>
    )
  }

  return (
    <Layout style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      position: 'relative'
    }}>
      {/* 背景装饰 */}
      <div style={{
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
        pointerEvents: 'none'
      }} />

      <Header style={{
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
        lineHeight: 'normal'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1, minWidth: 0 }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(102, 126, 234, 0.3)',
            flexShrink: 0
          }}>
            <MedicineBoxOutlined style={{ fontSize: '24px', color: 'white' }} />
          </div>
          <div style={{ flex: 1, minWidth: 0, overflow: 'visible' }}>
            <h1 style={{
              margin: 0,
              color: '#333',
              fontWeight: '700',
              fontSize: '20px',
              lineHeight: '28px',
              wordBreak: 'keep-all',
              whiteSpace: 'normal'
            }}>
              智能医疗管家平台
            </h1>
            <p style={{
              margin: '4px 0 0 0',
              color: '#666',
              fontSize: '14px',
              opacity: 0.8,
              lineHeight: '20px',
              wordBreak: 'keep-all',
              whiteSpace: 'normal'
            }}>
              专业的AI医疗咨询助手
            </p>
          </div>
        </div>

        <Space style={{ flexShrink: 0, marginLeft: '16px' }}>
          <Tag color="blue" style={{ fontSize: '13px', padding: '4px 12px', borderRadius: '16px' }}>
            🏥 患者端
          </Tag>
          <Tag color="green" style={{ fontSize: '13px', padding: '4px 12px', borderRadius: '16px' }}>
            🔒 安全可靠
          </Tag>
        </Space>
      </Header>

      <Content style={{
        padding: '32px',
        maxWidth: '1400px',
        margin: '0 auto',
        width: '100%',
        minHeight: 'calc(100vh - 80px)',
        position: 'relative',
        zIndex: 5
      }}>
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
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}
        >
          {/* 消息区域 */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px 0',
            position: 'relative'
          }}>
            {messages.length === 0 ? (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                padding: '40px'
              }}>
                <div style={{
                  width: '120px',
                  height: '120px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '24px',
                  boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)'
                }}>
                  <MedicineBoxOutlined style={{ fontSize: '48px', color: 'white' }} />
                </div>

                <h2 style={{
                  color: '#333',
                  fontSize: '24px',
                  fontWeight: '600',
                  marginBottom: '12px',
                  textAlign: 'center'
                }}>
                  欢迎使用智能医疗管家
                </h2>

                <p style={{
                  color: '#666',
                  fontSize: '16px',
                  textAlign: 'center',
                  lineHeight: '1.6',
                  marginBottom: '32px',
                  maxWidth: '500px'
                }}>
                  我是您的AI医疗助手，可以帮您解答健康问题、提供医疗建议。
                  请描述您的症状或咨询问题，我会基于专业医疗知识为您提供帮助。
                </p>

                <Space direction="vertical" size="large">
                  <Space wrap size="large">
                    <div style={{ textAlign: 'center' }}>
                      <HeartOutlined style={{ fontSize: '32px', color: '#ff4d4f', marginBottom: '8px' }} />
                      <div style={{ color: '#666', fontSize: '14px' }}>健康咨询</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <BulbOutlined style={{ fontSize: '32px', color: '#faad14', marginBottom: '8px' }} />
                      <div style={{ color: '#666', fontSize: '14px' }}>医学知识</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <MedicineBoxOutlined style={{ fontSize: '32px', color: '#52c41a', marginBottom: '8px' }} />
                      <div style={{ color: '#666', fontSize: '14px' }}>用药指导</div>
                    </div>
                  </Space>

                  <div style={{
                    background: 'rgba(102, 126, 234, 0.1)',
                    padding: '16px 24px',
                    borderRadius: '12px',
                    border: '1px solid rgba(102, 126, 234, 0.2)'
                  }}>
                    <div style={{ fontSize: '14px', color: '#666', textAlign: 'center' }}>
                      💡 <strong>温馨提示：</strong>本平台仅提供参考信息，不替代医生诊断。如有紧急情况，请立即就医。
                    </div>
                  </div>
                </Space>
              </div>
            ) : (
              <>
                {messages.map(renderMessage)}

                {/* 打字指示器 */}
                {isTyping && (
                  <div style={{
                    display: 'flex',
                    gap: '12px',
                    marginTop: '20px',
                    padding: '0 16px'
                  }}>
                    <Avatar
                      icon={<RobotOutlined />}
                      style={{
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)'
                      }}
                      size={40}
                    />
                    <div style={{
                      padding: '16px 20px',
                      borderRadius: '20px 20px 20px 4px',
                      background: '#ffffff',
                      boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      border: '1px solid rgba(0, 0, 0, 0.05)'
                    }}>
                      <Spin size="small" style={{ color: '#667eea' }} />
                      <span style={{ color: '#666', fontSize: '14px' }}>
                        AI正在思考中...
                      </span>
                    </div>
                  </div>
                )}
              </>
              )}

            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div style={{
            padding: '24px',
            background: 'rgba(248, 248, 248, 0.8)',
            borderTop: '1px solid rgba(0, 0, 0, 0.06)',
            backdropFilter: 'blur(10px)'
          }}>
            <div style={{
              display: 'flex',
              gap: '16px',
              alignItems: 'flex-end',
              maxWidth: '100%'
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
                  placeholder="请描述您的症状或健康问题，我会为您提供专业的医疗建议..."
              rows={3}
              disabled={chatMutation.isPending}
                  style={{
                    borderRadius: '16px',
                    border: '2px solid rgba(102, 126, 234, 0.2)',
                    fontSize: '15px',
                    resize: 'none',
                    transition: 'all 0.3s ease',
                    background: 'rgba(255, 255, 255, 0.9)',
                    backdropFilter: 'blur(10px)'
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
                <div style={{
                  fontSize: '12px',
                  color: '#999',
                  marginTop: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span>💡 按 Enter 发送消息，Shift + Enter 换行</span>
                  {input.length > 0 && (
                    <span style={{ color: '#667eea', fontWeight: '500' }}>
                      {input.length} 字符
                    </span>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <Tooltip title="上传图片进行医疗术语识别">
              <Upload
                beforeUpload={handleImageUpload}
                showUploadList={false}
                accept="image/*"
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
                        transition: 'all 0.3s ease'
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

              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={chatMutation.isPending}
                  disabled={!input.trim()}
                  style={{
                    borderRadius: '12px',
                    height: '56px',
                    width: '80px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: !input.trim() || chatMutation.isPending
                      ? '#d9d9d9'
                      : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none',
                    boxShadow: !input.trim() || chatMutation.isPending
                      ? 'none'
                      : '0 4px 16px rgba(102, 126, 234, 0.3)',
                    transition: 'all 0.3s ease'
                  }}
              >
                  {!chatMutation.isPending && <SendOutlined />}
              </Button>
              </div>
            </div>
          </div>
        </div>
      </Content>
    </Layout>
  )
}