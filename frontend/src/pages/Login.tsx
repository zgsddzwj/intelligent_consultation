import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Form, Input, Button, Typography, message, Tabs } from 'antd'
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  HeartOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import { authApi, saveAuthToken } from '../services/auth'

const { Title, Text } = Typography

// 左侧品牌展示区特性列表
const features = [
  { icon: <SafetyCertificateOutlined />, title: 'AI 智能问诊', desc: '基于 RAG + 知识图谱的专业医疗咨询' },
  { icon: <ExperimentOutlined />, title: '多模态诊断', desc: '支持文本、图片等多模态医学影像分析' },
  { icon: <TeamOutlined />, title: '医患协同', desc: '患者、医生、管理员多角色协作平台' },
]

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from || '/'
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('login')

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const data = await authApi.login(values)
      saveAuthToken(data.access_token, {
        id: data.user_id,
        username: data.username,
        role: data.role,
      })
      message.success('登录成功')
      navigate(from, { replace: true })
    } catch (err: any) {
      message.error(err.message || '登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (values: {
    username: string
    email: string
    password: string
    confirm: string
  }) => {
    setLoading(true)
    try {
      await authApi.register({
        username: values.username,
        email: values.email,
        password: values.password,
      })
      message.success('注册成功，请登录')
      setActiveTab('login')
    } catch (err: any) {
      message.error(err.message || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        background: 'var(--background-body)',
      }}
    >
      {/* ===== 左侧品牌展示区 ===== */}
      <div
        style={{
          flex: '1 1 55%',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0d9488 100%)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '60px 64px',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* 装饰光斑 */}
        <div
          style={{
            position: 'absolute',
            top: '-100px',
            right: '-100px',
            width: '400px',
            height: '400px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(37, 99, 235, 0.15) 0%, transparent 70%)',
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: '-150px',
            left: '-50px',
            width: '350px',
            height: '350px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(13, 148, 136, 0.12) 0%, transparent 70%)',
            pointerEvents: 'none',
          }}
        />

        {/* Logo + 标题 */}
        <div style={{ position: 'relative', zIndex: 1, maxWidth: '480px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '48px' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                background: 'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 8px 24px rgba(37, 99, 235, 0.3)',
              }}
            >
              <HeartOutlined style={{ fontSize: '28px', color: '#fff' }} />
            </div>
            <div>
              <Title level={3} style={{ color: '#fff', margin: 0, fontWeight: 700 }}>
                智能医疗管家
              </Title>
              <Text style={{ color: 'rgba(203, 213, 225, 0.7)', fontSize: '13px' }}>
                AI-Powered Medical Platform
              </Text>
            </div>
          </div>

          <Title
            level={2}
            style={{
              color: '#fff',
              fontWeight: 700,
              fontSize: '32px',
              lineHeight: 1.3,
              marginBottom: '16px',
            }}
          >
            专业的 AI 驱动<br />智能医疗咨询平台
          </Title>

          <Text style={{ color: 'rgba(203, 213, 225, 0.75)', fontSize: '15px', lineHeight: 1.7, display: 'block', marginBottom: '40px' }}>
            融合大语言模型、知识图谱与多模态诊断技术，<br />
            为患者提供精准的健康咨询，为医生赋能智能诊断辅助。
          </Text>

          {/* 特性列表 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {features.map((feat, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  animation: `fadeIn 0.5s ease ${idx * 0.1}s both`,
                }}
              >
                <div
                  style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '12px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#60a5fa',
                    fontSize: '20px',
                    flexShrink: 0,
                  }}
                >
                  {feat.icon}
                </div>
                <div>
                  <Text style={{ color: '#fff', fontSize: '15px', fontWeight: 600, display: 'block' }}>
                    {feat.title}
                  </Text>
                  <Text style={{ color: 'rgba(203, 213, 225, 0.6)', fontSize: '13px' }}>
                    {feat.desc}
                  </Text>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ===== 右侧表单区 ===== */}
      <div
        style={{
          flex: '1 1 45%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 32px',
          background: 'var(--background-white)',
        }}
      >
        <div style={{ width: '100%', maxWidth: '380px' }}>
          <div style={{ marginBottom: '32px' }}>
            <Title level={2} style={{ fontWeight: 700, marginBottom: '8px' }}>
              {activeTab === 'login' ? '欢迎回来' : '创建账户'}
            </Title>
            <Text type="secondary" style={{ fontSize: '14px' }}>
              {activeTab === 'login'
                ? '登录后使用 AI 健康咨询服务'
                : '注册账户，开启智能医疗体验'}
            </Text>
          </div>

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            centered
            items={[
              {
                key: 'login',
                label: '登录',
                children: (
                  <Form layout="vertical" onFinish={handleLogin} size="large" requiredMark={false}>
                    <Form.Item
                      name="username"
                      label="用户名"
                      rules={[{ required: true, message: '请输入用户名' }]}
                    >
                      <Input prefix={<UserOutlined />} placeholder="请输入用户名" autoComplete="username" />
                    </Form.Item>
                    <Form.Item
                      name="password"
                      label="密码"
                      rules={[{ required: true, message: '请输入密码' }]}
                    >
                      <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" autoComplete="current-password" />
                    </Form.Item>
                    <Form.Item style={{ marginBottom: '16px' }}>
                      <Button type="primary" htmlType="submit" loading={loading} block style={{ height: '46px' }}>
                        登录
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
              {
                key: 'register',
                label: '注册',
                children: (
                  <Form layout="vertical" onFinish={handleRegister} size="large" requiredMark={false}>
                    <Form.Item
                      name="username"
                      label="用户名"
                      rules={[{ required: true, message: '请输入用户名' }, { min: 3, message: '至少3个字符' }]}
                    >
                      <Input prefix={<UserOutlined />} placeholder="请输入用户名" />
                    </Form.Item>
                    <Form.Item
                      name="email"
                      label="邮箱"
                      rules={[
                        { required: true, message: '请输入邮箱' },
                        { type: 'email', message: '邮箱格式不正确' },
                      ]}
                    >
                      <Input prefix={<MailOutlined />} placeholder="请输入邮箱" />
                    </Form.Item>
                    <Form.Item
                      name="password"
                      label="密码"
                      rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '至少6个字符' }]}
                    >
                      <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
                    </Form.Item>
                    <Form.Item
                      name="confirm"
                      label="确认密码"
                      dependencies={['password']}
                      rules={[
                        { required: true, message: '请确认密码' },
                        ({ getFieldValue }) => ({
                          validator(_, value) {
                            if (!value || getFieldValue('password') === value) {
                              return Promise.resolve()
                            }
                            return Promise.reject(new Error('两次密码不一致'))
                          },
                        }),
                      ]}
                    >
                      <Input.Password prefix={<LockOutlined />} placeholder="请再次输入密码" />
                    </Form.Item>
                    <Form.Item style={{ marginBottom: '16px' }}>
                      <Button type="primary" htmlType="submit" loading={loading} block style={{ height: '46px' }}>
                        注册
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
            ]}
          />

          <div style={{ textAlign: 'center' }}>
            <Link to="/" style={{ fontSize: '13px' }}>
              暂不登录，以访客身份浏览 →
            </Link>
          </div>

          {/* 安全提示 */}
          <div
            style={{
              marginTop: '32px',
              padding: '12px 16px',
              borderRadius: '10px',
              background: 'var(--info-bg)',
              border: '1px solid var(--primary-100)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <SafetyCertificateOutlined style={{ color: 'var(--primary-color)', fontSize: '16px', flexShrink: 0 }} />
            <Text style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              您的数据通过加密传输，我们严格保护您的隐私安全
            </Text>
          </div>
        </div>
      </div>
    </div>
  )
}
