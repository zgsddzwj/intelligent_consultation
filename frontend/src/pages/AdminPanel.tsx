import { Card, Typography, Row, Col, Progress, Tag, Space, List, Table, Button, Badge } from 'antd'
import {
  SettingOutlined,
  UserOutlined,
  DatabaseOutlined,
  SecurityScanOutlined,
  BellOutlined,
  CloudServerOutlined,
  ApiOutlined,
  MonitorOutlined,
  TeamOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ExportOutlined,
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

// 系统状态数据
const systemStats = [
  { title: '系统运行时间', value: '99.97%', icon: <CloudServerOutlined />, color: '#16a34a', bg: '#f0fdf4' },
  { title: 'API请求/日', value: '128.5K', icon: <ApiOutlined />, color: '#2563eb', bg: '#eff6ff' },
  { title: '活跃用户', value: '3,842', icon: <TeamOutlined />, color: '#d97706', bg: '#fffbeb' },
  { title: '数据库大小', value: '2.4GB', icon: <DatabaseOutlined />, color: '#dc2626', bg: '#fef2f2' },
]

// 服务状态列表
const serviceStatus = [
  { name: 'FastAPI 后端', status: 'running', uptime: '15d 8h', cpu: '23%', memory: '45%' },
  { name: 'Neo4j 图数据库', status: 'running', uptime: '30d 2h', cpu: '12%', memory: '62%' },
  { name: 'Milvus 向量库', status: 'running', uptime: '7d 14h', cpu: '34%', memory: '78%' },
  { name: 'Redis 缓存', status: 'running', uptime: '30d 2h', cpu: '3%', memory: '28%' },
  { name: 'PostgreSQL', status: 'running', uptime: '60d 5h', cpu: '18%', memory: '52%' },
]

// 系统日志（最近）
const recentLogs = [
  { id: 1, time: '10:32:15', level: 'info', message: '用户登录成功 - admin@hospital.com' },
  { id: 2, time: '10:28:44', level: 'warn', message: 'API响应延迟超过阈值 - /api/v1/consultation/chat (2.3s)' },
  { id: 3, time: '10:25:11', level: 'info', message: '知识图谱数据同步完成 - 新增节点 156 个' },
  { id: 4, time: '10:20:33', level: 'error', message: '向量检索超时 - Milvus连接池耗尽，已自动扩容' },
  { id: 5, time: '10:15:02', level: 'info', message: '模型训练任务完成 - intent_classifier_v2.1' },
]

// 管理功能卡片
const adminFeatures = [
  { icon: <UserOutlined />, title: '用户管理', description: '管理用户账户、角色权限、访问控制', color: '#2563eb', action: '管理用户' },
  { icon: <DatabaseOutlined />, title: '数据管理', description: '数据库维护、备份恢复、数据迁移', color: '#0d9488', action: '查看数据' },
  { icon: <SecurityScanOutlined />, title: '安全设置', description: '安全策略、审计日志、威胁检测', color: '#d97706', action: '安全配置' },
  { icon: <MonitorOutlined />, title: '系统监控', description: '性能指标、服务健康、告警规则', color: '#dc2626', action: '监控面板' },
]

export default function AdminPanel() {
  const getLevelTag = (level: string) => {
    switch (level) {
      case 'info': return <Tag color="blue" style={{ fontSize: '11px' }}>INFO</Tag>
      case 'warn': return <Tag color="orange" style={{ fontSize: '11px' }}>WARN</Tag>
      case 'error': return <Tag color="red" style={{ fontSize: '11px' }}>ERROR</Tag>
      default: return null
    }
  }

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'running': return <CheckCircleOutlined style={{ color: '#16a34a', fontSize: '15px' }} />
      default: return <WarningOutlined style={{ color: '#d97706', fontSize: '15px' }} />
    }
  }

  // 表格列定义
  const columns = [
    {
      title: '服务名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong style={{ fontSize: '13px' }}>{text}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Space size="small">
          {getStatusDot(status)}
          <Text style={{ fontSize: '13px', color: status === 'running' ? '#16a34a' : '#d97706' }}>
            {status === 'running' ? '运行中' : '异常'}
          </Text>
        </Space>
      ),
    },
    {
      title: '运行时间',
      dataIndex: 'uptime',
      key: 'uptime',
      render: (text: string) => <Text type="secondary" style={{ fontSize: '13px' }}>{text}</Text>,
    },
    {
      title: 'CPU',
      dataIndex: 'cpu',
      key: 'cpu',
      render: (cpu: string) => {
        const val = parseInt(cpu)
        return (
          <Progress
            percent={val}
            size="small"
            strokeColor={val > 70 ? '#dc2626' : val > 40 ? '#d97706' : '#16a34a'}
            format={() => cpu}
            style={{ width: 80 }}
          />
        )
      },
    },
    {
      title: '内存',
      dataIndex: 'memory',
      key: 'memory',
      render: (memory: string) => {
        const val = parseInt(memory)
        return (
          <Progress
            percent={val}
            size="small"
            strokeColor={val > 70 ? '#dc2626' : val > 40 ? '#d97706' : '#16a34a'}
            format={() => memory}
            style={{ width: 80 }}
          />
        )
      },
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
        <Space>
          <Button icon={<SyncOutlined />}>刷新</Button>
          <Button type="primary" icon={<ExportOutlined />}>导出报告</Button>
        </Space>
      </div>

      {/* 系统概览统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        {systemStats.map((stat, idx) => (
          <Col xs={24} sm={12} lg={6} key={idx}>
            <Card
              style={{ borderRadius: '14px', border: '1px solid var(--border-color)' }}
              styles={{ body: { padding: '20px' } }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '12px',
                    background: stat.bg,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: stat.color,
                    fontSize: '18px',
                    flexShrink: 0,
                  }}
                >
                  {stat.icon}
                </div>
                <Text type="secondary" style={{ fontSize: '13px' }}>{stat.title}</Text>
              </div>
              <Title level={2} style={{ margin: 0, fontWeight: 800, fontSize: '28px', lineHeight: 1 }}>
                {stat.value}
              </Title>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 管理功能入口 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        {adminFeatures.map((feat, idx) => (
          <Col xs={24} sm={12} lg={6} key={idx}>
            <Card
              hoverable
              style={{ borderRadius: '14px', border: '1px solid var(--border-color)' }}
              styles={{ body: { padding: '20px' } }}
            >
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '12px',
                  background: `${feat.color}10`,
                  border: `1px solid ${feat.color}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '14px',
                  color: feat.color,
                  fontSize: '20px',
                }}
              >
                {feat.icon}
              </div>
              <Title level={5} style={{ marginBottom: '6px', fontWeight: 700 }}>{feat.title}</Title>
              <Paragraph type="secondary" style={{ fontSize: '13px', marginBottom: '12px', lineHeight: 1.6 }}>
                {feat.description}
              </Paragraph>
              <Button
                type="link"
                style={{ color: feat.color, padding: 0, fontWeight: 600, fontSize: '13px' }}
              >
                {feat.action} →
              </Button>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 服务监控和系统日志 */}
      <Row gutter={[16, 16]}>
        {/* 服务状态表格 */}
        <Col xs={24} lg={14}>
          <Card
            title={
              <Space>
                <MonitorOutlined style={{ color: '#0d9488' }} />
                <Text strong>服务状态监控</Text>
              </Space>
            }
            extra={<CheckCircleOutlined style={{ color: '#16a34a' }} />}
            style={{ borderRadius: '14px', border: '1px solid var(--border-color)' }}
            styles={{ body: { padding: '0 20px 20px' } }}
          >
            <Table
              dataSource={serviceStatus}
              columns={columns}
              rowKey="name"
              pagination={false}
              size="middle"
              style={{ marginTop: '12px' }}
            />
          </Card>
        </Col>

        {/* 系统日志 */}
        <Col xs={24} lg={10}>
          <Card
            title={
              <Space>
                <BellOutlined style={{ color: '#d97706' }} />
                <Text strong>最近系统日志</Text>
              </Space>
            }
            extra={<Badge count={recentLogs.filter(l => l.level === 'error').length} style={{ backgroundColor: '#dc2626' }} />}
            style={{ borderRadius: '14px', border: '1px solid var(--border-color)' }}
            styles={{ body: { padding: '0 20px 20px', maxHeight: '380px', overflowY: 'auto' } }}
          >
            <List
              dataSource={recentLogs}
              renderItem={(item) => (
                <div
                  style={{
                    padding: '10px 12px',
                    marginBottom: '6px',
                    borderRadius: '10px',
                    background:
                      item.level === 'error' ? 'var(--error-bg)' :
                      item.level === 'warn' ? 'var(--warning-bg)' :
                      'var(--background-warm)',
                    borderLeft: `3px solid ${
                      item.level === 'error' ? '#dc2626' :
                      item.level === 'warn' ? '#d97706' : '#2563eb'
                    }`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    {getLevelTag(item.level)}
                    <Text type="secondary" style={{ fontSize: '11px' }}>{item.time}</Text>
                  </div>
                  <Text style={{ fontSize: '13px', lineHeight: 1.5 }}>{item.message}</Text>
                </div>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
