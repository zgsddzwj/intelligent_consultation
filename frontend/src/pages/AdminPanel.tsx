import { useState, lazy, Suspense } from 'react'
import { Tabs, Typography, Space, Button, Spin } from 'antd'
import {
  SettingOutlined, UserOutlined, DatabaseOutlined,
  SecurityScanOutlined, MonitorOutlined, ExportOutlined,
} from '@ant-design/icons'

const { Text } = Typography

// 懒加载子组件
const UserManagement = lazy(() => import('../components/admin/UserManagement'))
const DataManagement = lazy(() => import('../components/admin/DataManagement'))
const SecuritySettings = lazy(() => import('../components/admin/SecuritySettings'))
const SystemMonitoring = lazy(() => import('../components/admin/SystemMonitoring'))
const ExportReport = lazy(() => import('../components/admin/ExportReport'))

const TabLoader = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
    <Spin size="large" />
  </div>
)

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState('users')

  const tabItems = [
    {
      key: 'users',
      label: (
        <Space>
          <UserOutlined />
          <span>用户管理</span>
        </Space>
      ),
      children: (
        <Suspense fallback={<TabLoader />}>
          <UserManagement />
        </Suspense>
      ),
    },
    {
      key: 'data',
      label: (
        <Space>
          <DatabaseOutlined />
          <span>数据管理</span>
        </Space>
      ),
      children: (
        <Suspense fallback={<TabLoader />}>
          <DataManagement />
        </Suspense>
      ),
    },
    {
      key: 'security',
      label: (
        <Space>
          <SecurityScanOutlined />
          <span>安全设置</span>
        </Space>
      ),
      children: (
        <Suspense fallback={<TabLoader />}>
          <SecuritySettings />
        </Suspense>
      ),
    },
    {
      key: 'monitor',
      label: (
        <Space>
          <MonitorOutlined />
          <span>系统监控</span>
        </Space>
      ),
      children: (
        <Suspense fallback={<TabLoader />}>
          <SystemMonitoring />
        </Suspense>
      ),
    },
    {
      key: 'export',
      label: (
        <Space>
          <ExportOutlined />
          <span>导出报告</span>
        </Space>
      ),
      children: (
        <Suspense fallback={<TabLoader />}>
          <ExportReport />
        </Suspense>
      ),
    },
  ]

  return (
    <div className="page-container">
      {/* 页面标题 */}
      <div className="page-title-bar">
        <div>
          <h2>
            <SettingOutlined style={{ color: '#6366f1' }} />
            管理后台
          </h2>
          <div className="subtitle">系统配置与运维管理中心</div>
        </div>
      </div>

      {/* 功能选项卡 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
        style={{ minHeight: '500px' }}
      />
    </div>
  )
}
