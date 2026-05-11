import { Layout, Card, Typography, Row, Col, Statistic, Progress, Tag, Space, Avatar, List, Badge } from 'antd'
import {
  MedicineBoxOutlined,
  UserOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  ScheduleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  RiseOutlined,
  HeartOutlined,
  ExperimentOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'

const { Header, Content } = Layout
const { Title, Text, Paragraph } = Typography

// 模拟数据
const mockStats = {
  totalPatients: 1284,
  todayConsultations: 56,
  pendingReviews: 12,
  avgResponseTime: '2.3min',
}

const recentActivities = [
  { id: 1, type: 'consultation', title: '新患者咨询', desc: '张先生 - 头痛症状咨询', time: '5分钟前', status: 'pending' },
  { id: 2, type: 'review', title: '诊断审核', desc: '李女士 - 血压异常报告', time: '15分钟前', status: 'reviewing' },
  { id: 3, type: 'complete', title: '问诊完成', desc: '王先生 - 用药指导完成', time: '30分钟前', status: 'completed' },
  { id: 4, type: 'consultation', title: '新患者咨询', desc: '赵女士 - 儿童发热咨询', time: '45分钟前', status: 'pending' },
]

const upcomingTasks = [
  { id: 1, title: '查看CT影像报告', patient: '陈先生', time: '09:30', priority: 'high' },
  { id: 2, title: '复诊随访提醒', patient: '刘女士', time: '10:00', priority: 'medium' },
  { id: 3, title: '会诊讨论准备', patient: '多学科团队', time: '14:00', priority: 'low' },
]

// 功能卡片配置
const featureCards = [
  {
    icon: <TeamOutlined />,
    title: '患者管理',
    description: '管理患者档案、病史记录、就诊信息',
    color: '#667eea',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  {
    icon: <FileTextOutlined />,
    title: '诊断辅助',
    description: 'AI辅助诊断、医学知识库查询、文献检索',
    color: '#10b981',
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
  },
  {
    icon: <ExperimentOutlined />,
    title: '用药指导',
    description: '药物相互作用检查、用药方案推荐',
    color: '#f59e0b',
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
  },
  {
    icon: <SafetyCertificateOutlined />,
    title: '数据分析',
    description: '诊疗数据统计、趋势分析、报告生成',
    color: '#ef4444',
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
  },
]

export default function DoctorDashboard() {
  const getStatusTag = (status: string) => {
    switch (status) {
      case 'pending':
        return <Tag color="processing" style={{ borderRadius: '20px' }}>待处理</Tag>
      case 'reviewing':
        return <Tag color="warning" style={{ borderRadius: '20px' }}>审核中</Tag>
      case 'completed':
        return <Tag color="success" style={{ borderRadius: '20px' }}>已完成</Tag>
      default:
        return null
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#ff4d4f'
      case 'medium': return '#faad14'
      case 'low': return '#52c41a'
      default: return '#8c8c8c'
    }
  }

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
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(16, 185, 129, 0.3)',
          }}>
            <MedicineBoxOutlined style={{ fontSize: '22px', color: 'white' }} />
          </div>
          <div>
            <Title level={4} style={{ margin: 0, fontWeight: 700, lineHeight: 1.3, fontSize: '17px' }}>
              医生工作台
            </Title>
            <Text type="secondary" style={{ fontSize: '12px' }}>专业医疗诊断与管理系统</Text>
          </div>
        </div>

        <Space size="small">
          <Badge dot status="processing" />
          <Text type="secondary" style={{ fontSize: '13px' }}>在线工作中</Text>
        </Space>
      </Header>

      <Content style={{ padding: '24px 32px', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
        {/* 统计卡片 */}
        <Row gutter={[20, 20]} style={{ marginBottom: '28px' }}>
          <Col xs={24} sm={12} lg={6}>
            <Card
              style={{
                borderRadius: '18px',
                border: 'none',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                overflow: 'hidden',
                position: 'relative',
              }}
              bodyStyle={{ padding: '24px', position: 'relative', zIndex: 1 }}
            >
              <div style={{ position: 'absolute', top: '-20px', right: '-20px', opacity: 0.08 }}>
                <UserOutlined style={{ fontSize: '120px', color: '#fff' }} />
              </div>
              <div style={{ position: 'relative', zIndex: 2 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                  <div style={{
                    width: '40px', height: '40px', borderRadius: '12px',
                    background: 'rgba(255,255,255,0.2)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                  }}>
                    <TeamOutlined style={{ fontSize: '18px', color: '#fff' }} />
                  </div>
                  <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: '13px' }}>总患者数</Text>
                </div>
                <Title level={2} style={{ color: '#fff', margin: 0, fontWeight: 800 }}>
                  {mockStats.totalPatients.toLocaleString()}
                </Title>
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <RiseOutlined style={{ color: 'rgba(255,255,255,0.8)', fontSize: '12px' }} />
                  <Text style={{ color: 'rgba(255,255,255,0.75)', fontSize: '12px' }}>较上月 +12.5%</Text>
                </div>
              </div>
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card
              style={{
                borderRadius: '18px',
                border: 'none',
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                overflow: 'hidden',
                position: 'relative',
              }}
              bodyStyle={{ padding: '24px', position: 'relative', zIndex: 1 }}
            >
              <div style={{ position: 'absolute', top: '-20px', right: '-20px', opacity: 0.08 }}>
                <ScheduleOutlined style={{ fontSize: '120px', color: '#fff' }} />
              </div>
              <div style={{ position: 'relative', zIndex: 2 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                  <div style={{
                    width: '40px', height: '40px', borderRadius: '12px',
                    background: 'rgba(255,255,255,0.2)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                  }}>
                    <ClockCircleOutlined style={{ fontSize: '18px', color: '#fff' }} />
                  </div>
                  <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: '13px' }}>今日问诊</Text>
                </div>
                <Title level={2} style={{ color: '#fff', margin: 0, fontWeight: 800 }}>
                  {mockStats.todayConsultations}
                </Title>
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <RiseOutlined style={{ color: 'rgba(255,255,255,0.8)', fontSize: '12px' }} />
                  <Text style={{ color: 'rgba(255,255,255,0.75)', fontSize: '12px' }}>较昨日 +8</Text>
                </div>
              </div>
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card
              style={{
                borderRadius: '18px',
                border: 'none',
                background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                overflow: 'hidden',
                position: 'relative',
              }}
              bodyStyle={{ padding: '24px', position: 'relative', zIndex: 1 }}
            >
              <div style={{ position: 'absolute', top: '-20px', right: '-20px', opacity: 0.08 }}>
                <FileTextOutlined style={{ fontSize: '120px', color: '#fff' }} />
              </div>
              <div style={{ position: 'relative', zIndex: 2 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                  <div style={{
                    width: '40px', height: '40px', borderRadius: '12px',
                    background: 'rgba(255,255,255,0.2)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                  }}>
                    <WarningOutlined style={{ fontSize: '18px', color: '#fff' }} />
                  </div>
                  <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: '13px' }}>待审阅</Text>
                </div>
                <Title level={2} style={{ color: '#fff', margin: 0, fontWeight: 800 }}>
                  {mockStats.pendingReviews}
                </Title>
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <ThunderboltOutlined style={{ color: 'rgba(255,255,255,0.8)', fontSize: '12px' }} />
                  <Text style={{ color: 'rgba(255,255,255,0.75)', fontSize: '12px' }}>需要关注</Text>
                </div>
              </div>
            </Card>
          </Col>

          <Col xs={24} sm={12} lg={6}>
            <Card
              style={{
                borderRadius: '18px',
                border: 'none',
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                overflow: 'hidden',
                position: 'relative',
              }}
              bodyStyle={{ padding: '24px', position: 'relative', zIndex: 1 }}
            >
              <div style={{ position: 'absolute', top: '-20px', right: '-20px', opacity: 0.08 }}>
                <ThunderboltOutlined style={{ fontSize: '120px', color: '#fff' }} />
              </div>
              <div style={{ position: 'relative', zIndex: 2 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                  <div style={{
                    width: '40px', height: '40px', borderRadius: '12px',
                    background: 'rgba(255,255,255,0.2)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                  }}>
                    <CheckCircleOutlined style={{ fontSize: '18px', color: '#fff' }} />
                  </div>
                  <Text style={{ color: 'rgba(255,255,255,0.85)', fontSize: '13px' }}>平均响应</Text>
                </div>
                <Title level={2} style={{ color: '#fff', margin: 0, fontWeight: 800 }}>
                  {mockStats.avgResponseTime}
                </Title>
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <CheckCircleOutlined style={{ color: 'rgba(255,255,255,0.8)', fontSize: '12px' }} />
                  <Text style={{ color: 'rgba(255,255,255,0.75)', fontSize: '12px' }}>优于平均</Text>
                </div>
              </div>
            </Card>
          </Col>
        </Row>

        {/* 功能模块 */}
        <Row gutter={[20, 20]} style={{ marginBottom: '28px' }}>
          {featureCards.map((card, idx) => (
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
                  e.currentTarget.style.boxShadow = `0 12px 32px ${card.color}20`
                  e.currentTarget.style.borderColor = `${card.color}30`
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                  e.currentTarget.style.borderColor = 'var(--border-color)'
                }}
              >
                <div style={{
                  width: '52px', height: '52px', borderRadius: '16px',
                  background: card.gradient, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  marginBottom: '18px', boxShadow: `0 8px 20px ${card.color}25`,
                }}>
                  <span style={{ fontSize: '24px', color: '#fff' }}>{card.icon}</span>
                </div>
                <Title level={5} style={{ marginBottom: '8px', fontWeight: 700 }}>{card.title}</Title>
                <Paragraph type="secondary" style={{ fontSize: '13px', marginBottom: 0, lineHeight: 1.6 }}>
                  {card.description}
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>

        {/* 最近活动和待办任务 */}
        <Row gutter={[20, 20]}>
          <Col xs={24} lg={14}>
            <Card
              title={
                <Space>
                  <ClockCircleOutlined style={{ color: 'var(--primary-color)' }} />
                  <Text strong>最近活动</Text>
                </Space>
              }
              style={{
                borderRadius: '18px',
                border: '1px solid var(--border-color)',
                boxShadow: 'var(--shadow-sm)',
              }}
              bodyStyle={{ padding: '0 24px 24px' }}
            >
              <List
                dataSource={recentActivities}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      padding: '14px 0',
                      borderBottom: '1px solid var(--divider-color)',
                      transition: 'background 0.2s ease',
                      borderRadius: '10px',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--background-warm)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          size={40}
                          icon={
                            item.type === 'consultation' ? <UserOutlined /> :
                            item.type === 'review' ? <FileTextOutlined /> : <CheckCircleOutlined />
                          }
                          style={{
                            background:
                              item.type === 'consultation' ? 'linear-gradient(135deg, #667eea, #764ba2)' :
                              item.type === 'review' ? 'linear-gradient(135deg, #faad14, #fa8c16)' :
                              'linear-gradient(135deg, #52c41a, #389e0d)',
                          }}
                        />
                      }
                      title={
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <Text strong style={{ fontSize: '14px' }}>{item.title}</Text>
                          {getStatusTag(item.status)}
                        </div>
                      }
                      description={
                        <div>
                          <Text type="secondary" style={{ fontSize: '13px' }}>{item.desc}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: '11px', marginTop: '4px', display: 'inline-block' }}>
                            {item.time}
                          </Text>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>

          <Col xs={24} lg={10}>
            <Card
              title={
                <Space>
                  <ScheduleOutlined style={{ color: '#f59e0b' }} />
                  <Text strong>待办任务</Text>
                </Space>
              }
              extra={<Badge count={upcomingTasks.length} style={{ backgroundColor: '#f59e0b' }} />}
              style={{
                borderRadius: '18px',
                border: '1px solid var(--border-color)',
                boxShadow: 'var(--shadow-sm)',
              }}
              bodyStyle={{ padding: '0 24px 24px' }}
            >
              <List
                dataSource={upcomingTasks}
                renderItem={(item) => (
                  <div
                    key={item.id}
                    style={{
                      padding: '14px 16px',
                      marginBottom: '10px',
                      borderRadius: '14px',
                      background: 'var(--background-warm)',
                      borderLeft: `3px solid ${getPriorityColor(item.priority)}`,
                      transition: 'all 0.2s ease',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateX(4px)'
                      e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateX(0)'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                      <div>
                        <Text strong style={{ fontSize: '14px', display: 'block', marginBottom: '4px' }}>
                          {item.title}
                        </Text>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          患者：{item.patient}
                        </Text>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <Tag
                          color={
                            item.priority === 'high' ? 'red' :
                            item.priority === 'medium' ? 'orange' : 'green'
                          }
                          style={{ borderRadius: '12px', fontSize: '11px' }}
                        >
                          {item.priority === 'high' ? '紧急' : item.priority === 'medium' ? '一般' : '低优'}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: '13px', display: 'block', marginTop: '4px' }}>
                          🕐 {item.time}
                        </Text>
                      </div>
                    </div>
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
