import { useState } from 'react'
import { Layout, Input, Button, List, Card, message, Upload } from 'antd'
import { SendOutlined, UploadOutlined } from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import { consultationApi, ChatRequest } from '../services/consultation'
import { useConsultationStore } from '../stores/consultation'
import api from '../services/api'

const { Header, Content } = Layout
const { TextArea } = Input

export default function PatientPortal() {
  const [input, setInput] = useState('')
  const { messages, consultationId, addMessage, setConsultationId } = useConsultationStore()

  const chatMutation = useMutation({
    mutationFn: (data: ChatRequest) => consultationApi.chat(data),
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
      setInput('')
    },
    onError: (error: any) => {
      message.error('发送消息失败: ' + (error.message || '未知错误'))
    },
  })

  const handleSend = () => {
    if (!input.trim()) return

    addMessage({
      role: 'user',
      content: input,
    })

    chatMutation.mutate({
      message: input,
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
      const analysisText = `图片分析结果：\n${response.analysis_result}\n\n提取的医疗术语：${JSON.stringify(response.medical_terms, null, 2)}`
      
      addMessage({
        role: 'user',
        content: `[图片] ${file.name}`,
      })
      
      addMessage({
        role: 'assistant',
        content: analysisText,
      })
      
      message.success('图片分析完成')
    } catch (error: any) {
      message.error('图片分析失败: ' + (error.message || '未知错误'))
    }
    return false // 阻止默认上传
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
        <h1 style={{ margin: 0, lineHeight: '64px' }}>智能医疗管家平台 - 患者端</h1>
      </Header>
      <Content style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        <Card style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px' }}>
            <List
              dataSource={messages}
              renderItem={(item, index) => (
                <List.Item key={index} style={{ border: 'none', padding: '8px 0' }}>
                  <div
                    style={{
                      width: '100%',
                      textAlign: item.role === 'user' ? 'right' : 'left',
                    }}
                  >
                    <div
                      style={{
                        display: 'inline-block',
                        maxWidth: '70%',
                        padding: '12px 16px',
                        borderRadius: '8px',
                        background: item.role === 'user' ? '#1890ff' : '#f0f0f0',
                        color: item.role === 'user' ? '#fff' : '#000',
                      }}
                    >
                      {item.content}
                      {item.sources && item.sources.length > 0 && (
                        <div style={{ marginTop: '8px', fontSize: '12px', opacity: 0.7 }}>
                          来源: {item.sources.join(', ')}
                        </div>
                      )}
                      {item.risk_level && (
                        <div style={{ marginTop: '8px', fontSize: '12px', color: '#ff4d4f' }}>
                          风险等级: {item.risk_level}
                        </div>
                      )}
                    </div>
                  </div>
                </List.Item>
              )}
            />
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="请输入您的问题..."
              rows={3}
              disabled={chatMutation.isPending}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <Upload
                beforeUpload={handleImageUpload}
                showUploadList={false}
                accept="image/*"
              >
                <Button icon={<UploadOutlined />} title="上传图片进行医疗术语识别">
                  图片
                </Button>
              </Upload>
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={chatMutation.isPending}
                style={{ height: 'auto' }}
              >
                发送
              </Button>
            </div>
          </div>
        </Card>
      </Content>
    </Layout>
  )
}

