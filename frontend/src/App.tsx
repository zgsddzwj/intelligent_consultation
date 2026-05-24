import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation, Link } from 'react-router-dom'
import { Layout, Menu, Typography, Space, Avatar, Breadcrumb, Drawer, Button } from 'antd'
import { ErrorBoundary } from './components/ErrorBoundary'
import {
  MedicineBoxOutlined,
  UserOutlined,
  SettingOutlined,
  ExperimentOutlined,
  HeartOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  HomeOutlined,
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

// 面包屑映射
const breadcrumbMap: Record<string, { title: string; icon: React.ReactNode }> = {
  '/': { title: '患者门户', icon: <UserOutlined /> },
  '/doctor': { title: '医生工作台', icon: <MedicineBoxOutlined /> },
  '/knowledge-graph': { title: '知识图谱', icon: <ExperimentOutlined /> },
  '/admin': { title: '管理后台', icon: <SettingOutlined /> },
}

/** 面包屑组件 */
function PageBreadcrumb() {
  const location = useLocation()
  const current = breadcrumbMap[location.pathname]

  if (!current) return null

  return (
    <Breadcrumb
      style={{
        marginBottom: '16px',
        padding: '0 4px',
      }}
      items={[
        {
          title: (
            <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <HomeOutlined />
              <span>首页</span>
            </Link>
          ),
        },
        {
          title: (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--primary-color)' }}>
              {current.icon}
              {current.title}
            </span>
          ),
        },
      ]}
    />
  )
}

// 应用布局组件 - 包含侧边导航（响应式）
function AppLayout() {
  const location = useLocation()
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

  const siderWidth = collapsed ? 80 : 260

  // 侧边栏内容
  const siderContent = (
    <>
      {/* Logo区域 */}
      <div
        style={{
          padding: collapsed ? '24px 12px' : '32px 24px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          transition: 'padding var(--transition-normal)',
        }}
      >
        <div
          style={{
            width: collapsed ? '44px' : '64px',
            height: collapsed ? '44px' : '64px',
            borderRadius: '20px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 32px rgba(102, 126, 234, 0.4)',
            animation: 'float 3s ease-in-out infinite',
            transition: 'all var(--transition-normal)',
            flexShrink: 0,
          }}
        >
          <HeartOutlined style={{ fontSize: collapsed ? '22px' : '30px', color: '#fff' }} />
        </div>
        {!collapsed && (
          <div style={{ textAlign: 'center', animation: 'fadeIn 0.3s ease' }}>
            <Title
              level={4}
              style={{
                color: '#fff',
                margin: 0,
                fontWeight: 700,
                fontSize: '17px',
                letterSpacing: '-0.02em',
              }}
            >
              智能医疗管家
            </Title>
            <Text
              style={{
                color: 'rgba(255,255,255,0.45)',
                fontSize: '12px',
                marginTop: '4px',
                display: 'block',
              }}
            >
              AI-Powered Medical Platform
            </Text>
          </div>
        )}
      </div>

      {/* 导航菜单 */}
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        inlineCollapsed={collapsed}
        style={{
          background: 'transparent',
          border: 'none',
          marginTop: '16px',
          padding: '0 12px',
        }}
        theme="dark"
        onClick={() => isMobile && setMobileOpen(false)}
      />

      {/* 底部信息 */}
      {!collapsed && (
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
              <Text
                style={{
                  color: '#fff',
                  fontSize: '13px',
                  fontWeight: 600,
                  display: 'block',
                  lineHeight: 1.3,
                }}
              >
                访客用户
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px', display: 'block' }}>
                v2.0 · 在线
              </Text>
            </div>
          </div>
        </div>
      )}
    </>
  )

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 桌面端侧边栏 */}
      {!isMobile && (
        <Sider
          width={260}
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
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
          {siderContent}
        </Sider>
      )}

      {/* 移动端抽屉侧边栏 */}
      {isMobile && (
        <Drawer
          placement="left"
          closable={false}
          onClose={() => setMobileOpen(false)}
          open={mobileOpen}
          width={260}
          bodyStyle={{ padding: 0, background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)' }}
        >
          {siderContent}
        </Drawer>
      )}

      {/* 主内容区 */}
      <Layout
        style={{
          marginLeft: isMobile ? 0 : siderWidth,
          transition: 'margin-left 0.3s ease',
        }}
      >
        {/* 移动端顶部栏 */}
        {isMobile && (
          <div
            style={{
              padding: '12px 16px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
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
              icon={<MenuUnfoldOutlined style={{ color: '#fff', fontSize: '20px' }} />}
              onClick={() => setMobileOpen(true)}
              style={{ padding: '4px' }}
            />
            <Text style={{ color: '#fff', fontSize: '16px', fontWeight: 600, flex: 1 }}>
              智能医疗管家
            </Text>
            <Avatar
              size={32}
              icon={<UserOutlined />}
              style={{ background: 'rgba(255,255,255,0.2)' }}
            />
          </div>
        )}

        <Content
          style={{
            minHeight: 'calc(100vh - 56px)',
            background: 'var(--background-light)',
            padding: isMobile ? '16px' : '24px 32px',
          }}
        >
          {/* 面包屑（非移动端首页） */}
          {location.pathname !== '/' && <PageBreadcrumb />}

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
            padding: isMobile ? '12px 16px' : '16px 24px',
          }}
        >
          <Space size="large" direction={isMobile ? 'vertical' : 'horizontal'}>
            <Text type="secondary" style={{ fontSize: '13px' }}>
              ©2026 智能医疗管家平台
            </Text>
            <Text type="secondary" style={{ fontSize: '13px' }}>
              本系统仅提供医疗信息参考，不替代医生诊断
            </Text>
          </Space>
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
            left: collapsed ? '72px' : '252px',
            top: '20px',
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
            transition: 'left 0.3s ease',
            color: 'var(--text-secondary)',
          }}
        />
      )}
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
