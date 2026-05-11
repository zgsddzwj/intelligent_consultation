import { Layout, Card, Typography, Row, Col, Statistic, Progress, Tag, Space, Avatar, List, Table, Switch, Button } from 'antd'
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
  FileTextOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ExportOutlined,
  PlusOutlined,
} from '@ant-design/icons'

const { Header, Content } = Layout
const { Title, Text, Paragraph } = Typography

// 系统状态数据
const systemStats = [
  {
    title: '系统运行时间',
    value: '99.97%',
    status: 'success',
    icon: <CloudServerOutlined />,
    color: '#10b981',
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
  },
  {
    title: 'API请求/日',
    value: '128.5K',
    status: 'normal',
    icon: <ApiOutlined />,
    color: '#667eea',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  {
    title: '活跃用户',
    value: '3,842',
    status: 'normal',
    icon: <TeamOutlined />,
    color: '#f59e0b',
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
  },
  {
    title: '数据库大小',
    value: '2.4GB',
    status: 'warning',
    icon: <DatabaseOutlined />,
    color: '#ef4444',
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
  },
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
  {
    icon: <UserOutlined />,
    title: '用户管理',
    description: '管理用户账户、角色权限、访问控制',
    color: '#667eea',
    action: '管理用户',
  },
  {
    icon: <DatabaseOutlined />,
    title: '数据管理',
    description: '数据库维护、备份恢复、数据迁移',
    color: '#10b981',
    action: '查看数据',
  },
  {
    icon: <SecurityScanOutlined />,
    title: '安全设置',
    description: '安全策略、审计日志、威胁检测',
    color: '#f59e0b',
    action: '安全配置',
  },
  {
    icon: <MonitorOutlined />,
    title: '系统监控',
    description: '性能指标、服务健康、告警规则',
    color: '#ef4444',
    action: '监控面板',
  },
]

export default function AdminPanel() {
  const getLevelTag = (level: string) => {
    switch (level) {
      case 'info': return <Tag color="blue" style={{ borderRadius: '12px', fontSize: '11px' }}>INFO</Tag>
      case 'warn': return <Tag color="orange" style={{ borderRadius: '12px', fontSize: '11px' }}>WARN</Tag>
      case 'error': return <Tag color="red" style={{ borderRadius: '12px', fontSize: '11px' }}>ERROR</Tag>
      default: return null
    }
  }

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'running': return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '16px' }} />
      default: return <WarningOutlined style={{ color: '#faad14', fontSize: '16px' }} />
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
          <Text style={{ fontSize: '13px', color: status === 'running' ? '#52c41a' : '#faad14' }}>
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
            strokeColor={val > 70 ? '#ff4d4f' : val > 40 ? '#faad14' : '#52c41a'}
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
            strokeColor={val > 70 ? '#ff4d4f' : val > 40 ? '#faad14' : '#52c41a'}
            format={() => memory}
            style={{ width: 80 }}
          />
        )
      },
    },
  ]

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
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.3)',
          }}>
            <SettingOutlined style={{ fontSize: '22px', color: 'white' }} />
          </div>
          <div>
            <Title level={4} style={{ margin: 0, fontWeight: 700, lineHeight: 1.3, fontSize: '17px' }}>
              管理后台
            </Title>
            <Text type="secondary" style={{ fontSize: '12px' }}>系统配置与运维管理中心</Text>
          </div>
        </div>

        <Space>
          <Button icon={<SyncOutlined />} style={{ borderRadius: '10px' }}>刷新</Button>
          <Button type="primary" icon={<ExportOutlined />} style={{ borderRadius: '10px' }}>导出报告</Button>
        </Space>
      </Header>

      <Content style={{ padding: '24px 32px', maxWidth: '1500px', margin: '0 auto', width: '100%' }}>
        {/* 系统概览统计 */}
        <Row gutter={[20, 20]} style={{ marginBottom: '28px' }}>
          {systemStats.map((stat, idx) => (
            <Col xs={24} sm={12} lg={6} key={idx}>
              <Card
                style={{
                  borderRadius: '18px',
                  border: 'none',
                  background: stat.gradient,
                  overflow: 'hidden',
                  position: 'relative',
                }}
                bodyStyle={{ padding: '24px', position: 'relative', zIndex: 1 }}
              >
                <div style={{
                  position: 'absolute', top: '-15px', right: '-15px',
                  opacity: 0.06,
                }}>
                  <span style={{ fontSize: '110px', color: '#fff' }}>{stat.icon}</span>
                </div>
                <div style={{ position: 'relative', zIndex: 2 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                    <div style={{
                      width: '38px', height: '38px', borderRadius: '12px',
                      background: 'rgba(255,255,255,0.2)', display: 'flex',
                      alignItems: 'center', justifyContent: 'center',
                    }}>
                      <span style={{ fontSize: '17px', color: '#fff' }}>{stat.icon}</span>
                    </div>
                    <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: '13px' }}>{stat.title}</Text>
                  </div>
                  <Title level={2} style={{ color: '#fff', margin: 0, fontWeight: 800 }}>
                    {stat.value}
                  </Title>
                </div>
              </Card>
            </Col>
          ))}
        </Row>

        {/* 管理功能入口 */}
        <Row gutter={[20, 20]} style={{ marginBottom: '28px' }}>
          {adminFeatures.map((feat, idx) => (
            <Col xs={24} sm={12} lg={6} key={idx}>
              <Card
                hoverable
                style={{
                  borderRadius: '18px',
                  border: '1px solid var(--border-color)',
                  transition: 'all 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
                  overflow: 'hidden',
                }}
                bodyStyle={{ padding: '24px' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)'
                  e.currentTarget.style.boxShadow = `0 12px 32px ${feat.color}20`
                  e.currentTarget.style.borderColor = `${feat.color}30`
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                  e.currentTarget.style.borderColor = 'var(--border-color)'
                }}
              >
                <div style={{
                  width: '50px', height: '50px', borderRadius: '16px',
                  background: `${feat.color}10`, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  marginBottom: '16px', border: `1px solid ${feat.color}20`,
                }}>
                  <span style={{ fontSize: '22px', color: feat.color }}>{feat.icon}</span>
                </div>
                <Title level={5} style={{ marginBottom: '6px', fontWeight: 700 }}>{feat.title}</Title>
                <Paragraph type="secondary" style={{ fontSize: '13px', marginBottom: '14px', lineHeight: 1.6 }}>
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
        <Row gutter={[20, 20]}>
          {/* 服务状态表格 */}
          <Col xs={24} lg={14}>
            <Card
              title={
                <Space>
                  <MonitorOutlined style={{ color: '#10b981' }} />
                  <Text strong>服务状态监控</Text>
                </Space>
              }
              extra={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              style={{
                borderRadius: '18px',
                border: '1px solid var(--border-color)',
                boxShadow: 'var(--shadow-sm)',
              }}
              bodyStyle={{ padding: '0 24px 24px' }}
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
                  <BellOutlined style={{ color: '#f59e0b' }} />
                  <Text strong>最近系统日志</Text>
                </Space>
              }
              extra={<Badge count={recentLogs.filter(l => l.level === 'error').length} style={{ backgroundColor: '#ff4d4f' }} />}
              style={{
                borderRadius: '18px',
                border: '1px solid var(--border-color)',
                boxShadow: 'var(--shadow-sm)',
              }}
              bodyStyle={{ padding: '0 24px 24px', maxHeight: '400px', overflowY: 'auto' }}
            >
              <List
                dataSource={recentLogs}
                renderItem={(item) => (
                  <div
                    style={{
                      padding: '12px 14px',
                      marginBottom: '8px',
                      borderRadius: '12px',
                      background:
                        item.level === 'error' ? 'var(--error-bg)' :
                        item.level === 'warn' ? 'var(--warning-bg)' :
                        'var(--background-warm)',
                      borderLeft: `3px solid ${
                        item.level === 'error' ? '#ff4d4f' :
                        item.level === 'warn' ? '#faad14' : '#1890ff'
                      }`,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
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
      </Content>
    </Layout>
  )
}
