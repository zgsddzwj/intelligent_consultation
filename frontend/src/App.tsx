import { Suspense, lazy, useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate, Link } from 'react-router-dom'
import { Layout, Menu, Typography, Avatar, Drawer, Button, Spin } from 'antd'
import ErrorBoundary from './components/ErrorBoundary'
import AuthGuard from './components/AuthGuard'
import {
  MedicineBoxOutlined,
  UserOutlined,
  SettingOutlined,
  ExperimentOutlined,
  HeartOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { getAuthUser, clearAuthToken, isAuthenticated } from './services/auth'
import type { MenuProps } from 'antd'

// ========== 代码分割 + 懒加载 ==========
const DoctorDashboard = lazy(() => import('./pages/DoctorDashboard'))
const PatientPortal = lazy(() => import('./pages/PatientPortal'))
const AdminPanel = lazy(() => import('./pages/AdminPanel'))
const KnowledgeGraph = lazy(() => import('./pages/KnowledgeGraph'))
const Login = lazy(() => import('./pages/Login'))

const PageLoader = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
    <Spin size="large" />
  </div>
)

const { Content, Footer, Sider } = Layout
const { Text } = Typography

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

/** 侧边栏内容 */
function SiderContent({ collapsed }: { collapsed: boolean }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [authUser, setAuthUser] = useState(getAuthUser())

  useEffect(() => {
    const onLogout = () => setAuthUser(null)
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [])

  const handleLogout = () => {
    clearAuthToken()
    setAuthUser(null)
    navigate('/')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Logo区域 */}
      <div
        style={{
          padding: collapsed ? '20px 12px' : '24px 20px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px',
          borderBottom: '1px solid var(--sidebar-border)',
          transition: 'padding var(--transition-normal)',
        }}
      >
        <div
          style={{
            width: collapsed ? '40px' : '48px',
            height: collapsed ? '40px' : '48px',
            borderRadius: '14px',
            background: 'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.3)',
            transition: 'all var(--transition-normal)',
            flexShrink: 0,
          }}
        >
          <HeartOutlined style={{ fontSize: collapsed ? '20px' : '24px', color: '#fff' }} />
        </div>
        {!collapsed && (
          <div style={{ textAlign: 'center', animation: 'fadeIn 0.3s ease' }}>
            <Text
              style={{
                color: '#fff',
                fontSize: '15px',
                fontWeight: 700,
                display: 'block',
                lineHeight: 1.3,
              }}
            >
              智能医疗管家
            </Text>
            <Text
              style={{
                color: 'var(--sidebar-text-muted)',
                fontSize: '11px',
                marginTop: '2px',
                display: 'block',
              }}
            >
              AI Medical Platform
            </Text>
          </div>
        )}
      </div>

      {/* 导航菜单 */}
      <div style={{ flex: 1, overflowY: 'auto', paddingTop: '12px' }}>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          inlineCollapsed={collapsed}
          style={{
            background: 'transparent',
            border: 'none',
            padding: '0 8px',
          }}
          theme="dark"
          onClick={({ key }) => navigate(key)}
        />
      </div>

      {/* 底部用户信息 */}
      <div
        style={{
          padding: collapsed ? '16px 8px' : '16px 16px',
          borderTop: '1px solid var(--sidebar-border)',
        }}
      >
        {collapsed ? (
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <Avatar
              size={36}
              icon={<UserOutlined />}
              style={{
                background: 'linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)',
                cursor: 'pointer',
              }}
            />
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              borderRadius: '12px',
              background: 'var(--sidebar-bg-hover)',
              border: '1px solid var(--sidebar-border)',
            }}
          >
            <Avatar
              size={32}
              icon={<UserOutlined />}
              style={{
                background: 'linear-gradient(135deg, #0d9488 0%, #14b8a6 100%)',
                flexShrink: 0,
              }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <Text
                style={{
                  color: '#fff',
                  fontSize: '13px',
                  fontWeight: 600,
                  display: 'block',
                  lineHeight: 1.3,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {authUser?.username || (isAuthenticated() ? '已登录' : '访客')}
              </Text>
              {authUser ? (
                <Text
                  onClick={handleLogout}
                  style={{
                    color: 'var(--sidebar-text-muted)',
                    fontSize: '11px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '2px',
                  }}
                >
                  <LogoutOutlined /> 退出登录
                </Text>
              ) : (
                <Link to="/login" style={{ color: 'var(--sidebar-text-muted)', fontSize: '11px' }}>
                  登录 / 注册
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// 应用布局组件
function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  // 检测移动端
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
      if (window.innerWidth >= 768) {
        setMobileOpen(false)
      }
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const siderWidth = collapsed ? 80 : 240

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 桌面端侧边栏 */}
      {!isMobile && (
        <Sider
          width={240}
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
          style={{
            background: 'var(--sidebar-bg)',
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            zIndex: 100,
            overflow: 'hidden',
          }}
        >
          <SiderContent collapsed={collapsed} />
        </Sider>
      )}

      {/* 移动端抽屉 */}
      {isMobile && (
        <Drawer
          placement="left"
          closable={false}
          onClose={() => setMobileOpen(false)}
          open={mobileOpen}
          width={240}
          styles={{ body: { padding: 0, background: 'var(--sidebar-bg)' } }}
        >
          <SiderContent collapsed={false} />
        </Drawer>
      )}

      {/* 主内容区 */}
      <Layout
        style={{
          marginLeft: isMobile ? 0 : siderWidth,
          transition: 'margin-left 0.25s ease',
          background: 'var(--background-body)',
          height: '100vh',
          overflow: 'hidden',
        }}
>
        {/* 移动端顶部栏 */}
        {isMobile && (
          <div
            style={{
              padding: '10px 16px',
              background: 'var(--sidebar-bg)',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              position: 'sticky',
              top: 0,
              zIndex: 50,
            }}
          >
            <Button
              type="text"
              icon={<MenuUnfoldOutlined style={{ color: '#fff', fontSize: '18px' }} />}
              onClick={() => setMobileOpen(true)}
            />
            <Text style={{ color: '#fff', fontSize: '15px', fontWeight: 600, flex: 1 }}>
              智能医疗管家
            </Text>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <HeartOutlined style={{ fontSize: '16px', color: '#fff' }} />
            </div>
          </div>
        )}

        <Content
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            overflowX: 'hidden',
            padding: 0,
          }}
>
          <ErrorBoundary>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<PatientPortal />} />
                <Route
                  path="/doctor"
                  element={
                    <AuthGuard requireAuth allowedRoles={['doctor', 'admin']}>
                      <DoctorDashboard />
                    </AuthGuard>
                  }
                />
                <Route
                  path="/admin"
                  element={
                    <AuthGuard requireAuth allowedRoles={['admin']}>
                      <AdminPanel />
                    </AuthGuard>
                  }
                />
                <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </Content>

        {/* 页脚 */}
        <Footer
          style={{
            textAlign: 'center',
            background: 'var(--background-white)',
            borderTop: '1px solid var(--border-color)',
            padding: '12px 24px',
          }}
        >
          <Text type="secondary" style={{ fontSize: '12px' }}>
            ©2026 智能医疗管家平台 · 本系统仅提供医疗信息参考，不替代医生诊断 · v3.1.0
          </Text>
        </Footer>
      </Layout>

      {/* 桌面端折叠按钮 */}
      {!isMobile && (
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={() => setCollapsed(!collapsed)}
          style={{
            position: 'fixed',
            left: collapsed ? '72px' : '232px',
            top: '16px',
            zIndex: 101,
            width: '24px',
            height: '24px',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--background-white)',
            border: '1px solid var(--border-color)',
            borderRadius: '50%',
            boxShadow: 'var(--shadow-sm)',
            transition: 'left 0.25s ease',
            color: 'var(--text-secondary)',
          }}
        />
      )}
    </Layout>
  )
}

// 根组件
function App() {
  const location = useLocation()
  const isLoginPage = location.pathname === '/login'

  if (isLoginPage) {
    return (
      <ErrorBoundary>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/login" element={<Login />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    )
  }

  return <AppLayout />
}

function AppWithRouter() {
  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  )
}

export default AppWithRouter
