import { useState, useCallback, useEffect } from 'react'
import { Row, Col, Card, Statistic, Spin, message, Table, Tag, Progress } from 'antd'
import {
  DatabaseOutlined, FileTextOutlined, TeamOutlined,
  MessageOutlined, CloudServerOutlined,
} from '@ant-design/icons'
import { adminApi, type DataStats } from '../../services/admin'
import { ApiError } from '../../services/api'

export default function DataManagement() {
  const [stats, setStats] = useState<DataStats | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    try {
      const res = await adminApi.getDataStats()
      setStats(res)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '加载数据统计失败'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  if (loading && !stats) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!stats) {
    return <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>暂无数据</div>
  }

  const agentRows = Object.entries(stats.consultations.by_agent).map(([type, count]) => ({
    key: type,
    agent_type: type,
    count,
    percentage: stats.consultations.total > 0 ? Math.round((count / stats.consultations.total) * 100) : 0,
  }))

  const agentColumns = [
    { title: 'Agent 类型', dataIndex: 'agent_type', key: 'agent_type' },
    { title: '咨询数', dataIndex: 'count', key: 'count' },
    {
      title: '占比',
      dataIndex: 'percentage',
      key: 'percentage',
      render: (val: number) => <Progress percent={val} size="small" style={{ width: 120 }} />,
    },
  ]

  return (
    <div>
      {/* 用户数据 */}
      <Card
        title={<><TeamOutlined style={{ marginRight: '8px', color: '#2563eb' }} />用户数据</>}
        size="small"
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic title="总用户数" value={stats.users.total} prefix={<TeamOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="活跃用户" value={stats.users.active} valueStyle={{ color: '#16a34a' }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="医生" value={stats.users.doctors} valueStyle={{ color: '#2563eb' }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="管理员" value={stats.users.admins} valueStyle={{ color: '#dc2626' }} />
          </Col>
        </Row>
      </Card>

      {/* 咨询数据 */}
      <Card
        title={<><MessageOutlined style={{ marginRight: '8px', color: '#0d9488' }} />咨询数据</>}
        size="small"
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      >
        <Row gutter={[16, 16]} style={{ marginBottom: '16px' }}>
          <Col xs={12} sm={8}>
            <Statistic title="总咨询数" value={stats.consultations.total} prefix={<MessageOutlined />} />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic title="已完成" value={stats.consultations.completed} valueStyle={{ color: '#16a34a' }} />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="完成率"
              value={stats.consultations.total > 0 ? Math.round((stats.consultations.completed / stats.consultations.total) * 100) : 0}
              suffix="%"
            />
          </Col>
        </Row>
        <Table
          dataSource={agentRows}
          columns={agentColumns}
          pagination={false}
          size="small"
        />
      </Card>

      {/* 知识文档数据 */}
      <Card
        title={<><FileTextOutlined style={{ marginRight: '8px', color: '#d97706' }} />知识文档数据</>}
        size="small"
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic title="文档总数" value={stats.knowledge_documents.total} prefix={<FileTextOutlined />} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="已索引" value={stats.knowledge_documents.indexed} valueStyle={{ color: '#16a34a' }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="未索引" value={stats.knowledge_documents.unindexed} valueStyle={{ color: '#d97706' }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="文件总大小"
              value={stats.knowledge_documents.total_file_size_bytes > 0
                ? (stats.knowledge_documents.total_file_size_bytes / 1024 / 1024).toFixed(2)
                : '0'}
              suffix="MB"
            />
          </Col>
        </Row>
      </Card>

      {/* 数据库概览 */}
      <Card
        title={<><DatabaseOutlined style={{ marginRight: '8px', color: '#dc2626' }} />数据库概览</>}
        size="small"
        style={{ borderRadius: '12px' }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8}>
            <Statistic
              title="数据库大小"
              value={stats.database.size_mb}
              suffix="MB"
              prefix={<DatabaseOutlined />}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="大小（字节）"
              value={stats.database.size_bytes}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="存储类型"
              value="PostgreSQL"
              prefix={<CloudServerOutlined />}
            />
          </Col>
        </Row>
      </Card>
    </div>
  )
}
