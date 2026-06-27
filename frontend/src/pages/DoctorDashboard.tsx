import { Card, Typography, Row, Col, Tag, Space, Avatar, List, Badge } from 'antd'
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
  ExperimentOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'

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

// 统计卡片配置
const statCards = [
  { label: '总患者数', value: mockStats.totalPatients.toLocaleString(), icon: <TeamOutlined />, color: '#2563eb', bg: '#eff6ff', trend: '+12.5%' },
  { label: '今日问诊', value: mockStats.todayConsultations, icon: <ClockCircleOutlined />, color: '#0d9488', bg: '#f0fdfa', trend: '+8' },
  { label: '待审阅', value: mockStats.pendingReviews, icon: <WarningOutlined />, color: '#d97706', bg: '#fffbeb', trend: '需关注' },
  { label: '平均响应', value: mockStats.avgResponseTime, icon: <CheckCircleOutlined />, color: '#16a34a', bg: '#f0fdf4', trend: '优于平均' },
]

// 功能卡片配置
const featureCards = [
  { icon: <TeamOutlined />, title: '患者管理', description: '管理患者档案、病史记录、就诊信息', color: '#2563eb' },
  { icon: <FileTextOutlined />, title: '诊断辅助', description: 'AI辅助诊断、医学知识库查询、文献检索', color: '#0d9488' },
  { icon: <ExperimentOutlined />, title: '用药指导', description: '药物相互作用检查、用药方案推荐', color: '#d97706' },
  { icon: <SafetyCertificateOutlined />, title: '数据分析', description: '诊疗数据统计、趋势分析、报告生成', color: '#dc2626' },
]

export default function DoctorDashboard() {
  const getStatusTag = (status: string) => {
    switch (status) {
      case 'pending':
        return <Tag color="processing">待处理</Tag>
      case 'reviewing':
        return <Tag color="warning">审核中</Tag>
      case 'completed':
        return <Tag color="success">已完成</Tag>
      default:
        return null
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#dc2626'
      case 'medium': return '#d97706'
      case 'low': return '#16a34a'
      default: return '#64748b'
    }
  }

  return (
    <div className="page-container">
      {/* 页面标题 */}
      <div className="page-title-bar">
        <div>
          <h2>
            <MedicineBoxOutlined style={{ color: 'var(--primary-color)' }} />
            医生工作台
          </h2>
          <div className="subtitle">专业医疗诊断与管理系统</div>
        </div>
        <Space>
          <Badge dot status="processing" />
          <Text type="secondary" style={{ fontSize: '13px' }}>在线工作中</Text>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        {statCards.map((stat, idx) => (
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
                <Text type="secondary" style={{ fontSize: '13px' }}>{stat.label}</Text>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                <Title level={2} style={{ margin: 0, fontWeight: 800, fontSize: '28px', lineHeight: 1 }}>
                  {stat.value}
                </Title>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                  <RiseOutlined style={{ color: stat.color, fontSize: '12px' }} />
                  <Text style={{ color: stat.color, fontSize: '12px', fontWeight: 600 }}>{stat.trend}</Text>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 功能模块 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        {featureCards.map((card, idx) => (
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
                  background: `${card.color}10`,
                  border: `1px solid ${card.color}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '14px',
                  color: card.color,
                  fontSize: '20px',
                }}
              >
                {card.icon}
              </div>
              <Title level={5} style={{ marginBottom: '6px', fontWeight: 700 }}>{card.title}</Title>
              <Paragraph type="secondary" style={{ fontSize: '13px', marginBottom: 0, lineHeight: 1.6 }}>
                {card.description}
              </Paragraph>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 最近活动和待办任务 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card
            title={
              <Space>
                <ClockCircleOutlined style={{ color: 'var(--primary-color)' }} />
                <Text strong>最近活动</Text>
              </Space>
            }
            style={{ borderRadius: '14px', border: '1px solid var(--border-color)' }}
            styles={{ body: { padding: '0 20px 20px' } }}
          >
            <List
              dataSource={recentActivities}
              renderItem={(item) => (
                <List.Item style={{ padding: '12px 0', borderBottom: '1px solid var(--divider-color)' }}>
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        size={36}
                        icon={
                          item.type === 'consultation' ? <UserOutlined /> :
                          item.type === 'review' ? <FileTextOutlined /> : <CheckCircleOutlined />
                        }
                        style={{
                          background:
                            item.type === 'consultation' ? 'var(--primary-50)' :
                            item.type === 'review' ? 'var(--warning-bg)' :
                            'var(--success-bg)',
                          color:
                            item.type === 'consultation' ? 'var(--primary-color)' :
                            item.type === 'review' ? 'var(--warning-color)' :
                            'var(--success-color)',
                        }}
                      />
                    }
                    title={
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Text strong style={{ fontSize: '14px' }}>{item.title}</Text>
                        {getStatusTag(item.status)}
                      </div>
                    }
                    description={
                      <div>
                        <Text type="secondary" style={{ fontSize: '13px' }}>{item.desc}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: '11px' }}>{item.time}</Text>
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
                <ScheduleOutlined style={{ color: '#d97706' }} />
                <Text strong>待办任务</Text>
              </Space>
            }
            extra={<Badge count={upcomingTasks.length} style={{ backgroundColor: '#d97706' }} />}
            style={{ borderRadius: '14px', border: '1px solid var(--border-color)' }}
            styles={{ body: { padding: '0 20px 20px' } }}
          >
            <List
              dataSource={upcomingTasks}
              renderItem={(item) => (
                <div
                  key={item.id}
                  style={{
                    padding: '12px 14px',
                    marginBottom: '8px',
                    borderRadius: '10px',
                    background: 'var(--background-warm)',
                    borderLeft: `3px solid ${getPriorityColor(item.priority)}`,
                    transition: 'all 0.2s ease',
                    cursor: 'pointer',
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
                        style={{ fontSize: '11px' }}
                      >
                        {item.priority === 'high' ? '紧急' : item.priority === 'medium' ? '一般' : '低优'}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginTop: '4px' }}>
                        {item.time}
                      </Text>
                    </div>
                  </div>
                </div>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
