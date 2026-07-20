import { useState, useCallback, useEffect } from 'react'
import {
  Card, Spin, message, Tag, Table, Progress, Row, Col,
  Statistic, Alert, Button, Space, Typography,
} from 'antd'
import {
  MonitorOutlined, ReloadOutlined, CheckCircleOutlined,
  WarningOutlined, CloseCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import { adminApi, type SystemMetrics } from '../../services/admin'
import { ApiError } from '../../services/api'

const { Text } = Typography

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${d}天 ${h}时 ${m}分`
}

const componentLabels: Record<string, string> = {
  database: 'PostgreSQL 数据库',
  redis: 'Redis 缓存',
  neo4j: 'Neo4j 知识图谱',
  milvus: 'Milvus 向量库',
  llm: 'LLM 服务',
}

export default function SystemMonitoring() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchMetrics = useCallback(async () => {
    setLoading(true)
    try {
      const res = await adminApi.getSystemMetrics()
      setMetrics(res)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '加载系统指标失败'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
  }, [fetchMetrics])

  if (loading && !metrics) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!metrics) {
    return <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>暂无数据</div>
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleOutlined style={{ color: '#16a34a', fontSize: '16px' }} />
      case 'unhealthy':
      case 'timeout':
        return <CloseCircleOutlined style={{ color: '#dc2626', fontSize: '16px' }} />
      default:
        return <WarningOutlined style={{ color: '#d97706', fontSize: '16px' }} />
    }
  }

  const getStatusTag = (status: string) => {
    const cfg: Record<string, { color: string; text: string }> = {
      healthy: { color: 'success', text: '健康' },
      unhealthy: { color: 'error', text: '异常' },
      timeout: { color: 'error', text: '超时' },
      degraded: { color: 'warning', text: '降级' },
    }
    const c = cfg[status] || { color: 'default', text: status }
    return <Tag color={c.color}>{c.text}</Tag>
  }

  // 组件表格数据
  const componentRows = Object.entries(metrics.components).map(([name, info]) => ({
    key: name,
    name: componentLabels[name] || name,
    status: info.status,
    error: info.error || '',
    extra: Object.entries(info)
      .filter(([k]) => !['status', 'error'].includes(k))
      .map(([k, v]) => `${k}: ${v}`)
      .join(', '),
  }))

  const componentColumns = [
    {
      title: '服务',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Space>
          {getStatusIcon(status)}
          {getStatusTag(status)}
        </Space>
      ),
    },
    {
      title: '详情',
      key: 'extra',
      render: (_: any, record: any) => (
        <Text type="secondary" style={{ fontSize: '12px' }}>
          {record.error || record.extra || '-'}
        </Text>
      ),
    },
  ]

  // 性能指标表格
  const perfRows = Object.entries(metrics.performance).map(([name, data]) => ({
    key: name,
    name,
    count: data.count,
    avg: `${(data.avg * 1000).toFixed(1)}ms`,
    p95: `${(data.p95 * 1000).toFixed(1)}ms`,
    max: `${(data.max * 1000).toFixed(1)}ms`,
    latest: `${(data.latest * 1000).toFixed(1)}ms`,
  }))

  const perfColumns = [
    { title: '指标', dataIndex: 'name', key: 'name' },
    { title: '调用次数', dataIndex: 'count', key: 'count', width: 80 },
    { title: '平均', dataIndex: 'avg', key: 'avg', width: 80 },
    { title: 'P95', dataIndex: 'p95', key: 'p95', width: 80 },
    { title: '最大', dataIndex: 'max', key: 'max', width: 80 },
    { title: '最新', dataIndex: 'latest', key: 'latest', width: 80 },
  ]

  // 告警列表
  const alertRows = Object.entries(metrics.alerts).map(([name, info]) => ({
    key: name,
    name,
    value: info.value,
    threshold: info.threshold,
    severity: info.severity,
  }))

  return (
    <div>
      {/* 概览统计 */}
      <Row gutter={[12, 12]} style={{ marginBottom: '16px' }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <Statistic
              title="运行时间"
              value={formatUptime(metrics.uptime_seconds)}
              prefix={<ClockCircleOutlined style={{ color: '#16a34a' }} />}
              valueStyle={{ fontSize: '16px' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <Statistic title="版本" value={metrics.version} prefix={<MonitorOutlined style={{ color: '#2563eb' }} />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <Statistic
              title="环境"
              value={metrics.environment}
              valueStyle={{ color: metrics.environment === 'production' ? '#dc2626' : '#d97706' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <Statistic
              title="告警数"
              value={Object.keys(metrics.alerts).length}
              valueStyle={{ color: Object.keys(metrics.alerts).length > 0 ? '#dc2626' : '#16a34a' }}
              prefix={Object.keys(metrics.alerts).length > 0 ? <WarningOutlined /> : <CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 刷新按钮 */}
      <div style={{ marginBottom: '12px' }}>
        <Button icon={<ReloadOutlined />} onClick={fetchMetrics} loading={loading}>
          刷新指标
        </Button>
      </div>

      {/* 告警区域 */}
      {Object.keys(metrics.alerts).length > 0 && (
        <Alert
          type="warning"
          message={`检测到 ${Object.keys(metrics.alerts).length} 个告警`}
          description={
            <Table
              dataSource={alertRows}
              columns={[
                { title: '告警项', dataIndex: 'name', key: 'name' },
                { title: '当前值', dataIndex: 'value', key: 'value', render: (v: number) => v.toFixed(2) },
                { title: '阈值', dataIndex: 'threshold', key: 'threshold' },
                {
                  title: '级别',
                  dataIndex: 'severity',
                  key: 'severity',
                  render: (s: string) => <Tag color={s === 'critical' ? 'red' : 'orange'}>{s}</Tag>,
                },
              ]}
              pagination={false}
              size="small"
            />
          }
          style={{ marginBottom: '16px', borderRadius: '12px' }}
        />
      )}

      {/* 服务状态 */}
      <Card
        title={<><MonitorOutlined style={{ marginRight: '8px', color: '#0d9488' }} />服务状态</>}
        size="small"
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      >
        <Table
          dataSource={componentRows}
          columns={componentColumns}
          pagination={false}
          size="small"
        />
      </Card>

      {/* 性能指标 */}
      <Card
        title="性能指标 (Profiler)"
        size="small"
        style={{ borderRadius: '12px' }}
      >
        {perfRows.length > 0 ? (
          <Table
            dataSource={perfRows}
            columns={perfColumns}
            pagination={false}
            size="small"
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
            暂无性能采样数据
          </div>
        )}
      </Card>
    </div>
  )
}
