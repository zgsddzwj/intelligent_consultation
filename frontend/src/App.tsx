import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { Layout, Menu, Typography, Space, Avatar } from 'antd'
import { ErrorBoundary } from './components/ErrorBoundary'
import {
  MedicineBoxOutlined,
  UserOutlined,
  DashboardOutlined,
  SettingOutlined,
  ExperimentOutlined,
  HeartOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import DoctorDashboard from './pages/DoctorDashboard'
import PatientPortal from './pages/PatientPortal'
import AdminPanel from './pages/AdminPanel'
import KnowledgeGraph from './pages/KnowledgeGraph'

const { Content, Footer, Sider } = Layout
const { Text, Title } = Typography

// 导航菜单项配置
const menuItems: MenuProps['items'] = [
  {
    key: '/',
    icon: <UserOutlined />,
    label: '患者门户',
  },
  {
    key: '/doctor',
    icon: <MedicineBoxOutlined />,
    label: '医生工作台',
  },
  {
    key: '/knowledge-graph',
    icon: <ExperimentOutlined />,
    label: '知识图谱',
  },
  {
    key: '/admin',
    icon: <SettingOutlined />,
    label: '管理后台',
  },
]

// 应用布局组件 - 包含侧边导航
function AppLayout() {
  const location = useLocation()
  
  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 侧边导航栏 */}
      <Sider
        width={260}
        style={{
          background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          overflow: 'auto',
        }}
      >
        {/* Logo区域 */}
        <div
          style={{
            padding: '32px 24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '20px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 8px 32px rgba(102, 126, 234, 0.4)',
              animation: 'float 3s ease-in-out infinite',
            }}
          >
            <HeartOutlined style={{ fontSize: '30px', color: '#fff' }} />
          </div>
          <div style={{ textAlign: 'center' }}>
            <Title level={4} style={{
              color: '#fff',
              margin: 0,
              fontWeight: 700,
              fontSize: '17px',
              letterSpacing: '-0.02em',
            }}>
              智能医疗管家
            </Title>
            <Text style={{
              color: 'rgba(255,255,255,0.45)',
              fontSize: '12px',
              marginTop: '4px',
              display: 'block',
            }}>
              AI-Powered Medical Platform
            </Text>
          </div>
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{
            background: 'transparent',
            border: 'none',
            marginTop: '16px',
            padding: '0 12px',
          }}
          theme="dark"
        />

        {/* 底部信息 */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            padding: '20px 24px',
            borderTop: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px 14px',
              borderRadius: '14px',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <Avatar
              size={36}
              icon={<UserOutlined />}
              style={{
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                flexShrink: 0,
              }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <Text style={{ color: '#fff', fontSize: '13px', fontWeight: 600, display: 'block', lineHeight: 1.3 }}>
                访客用户
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px', display: 'block' }}>
                v2.0 · 在线
              </Text>
            </div>
          </div>
        </div>
      </Sider>

      {/* 主内容区 */}
      <Layout style={{ marginLeft: 260, transition: 'margin-left 0.3s ease' }}>
        <Content
          style={{
            minHeight: 'calc(100vh - 56px)',
            background: 'var(--background-light)',
          }}
        >
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<PatientPortal />} />
              <Route path="/doctor" element={<DoctorDashboard />} />
              <Route path="/admin" element={<AdminPanel />} />
              <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
            </Routes>
          </ErrorBoundary>
        </Content>

        {/* 页脚 */}
        <Footer
          style={{
            textAlign: 'center',
            background: 'var(--background-white)',
            borderTop: '1px solid var(--border-color)',
            padding: '16px 24px',
          }}
        >
          <Space size="large">
            <Text type="secondary" style={{ fontSize: '13px' }}>
              ©2026 智能医疗管家平台
            </Text>
            <Text type="secondary" style={{ fontSize: '13px' }}>
              本系统仅提供医疗信息参考，不替代医生诊断
            </Text>
          </Space>
        </Footer>
      </Layout>
    </Layout>
  )
}

// 根组件
function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}

export default App
