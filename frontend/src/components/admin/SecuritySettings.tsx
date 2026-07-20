import { useState, useCallback, useEffect } from 'react'
import {
  Card, Spin, message, Tag, Descriptions, Switch, Table,
  Row, Col, Alert, Typography,
} from 'antd'
import {
  SecurityScanOutlined, LockOutlined, KeyOutlined,
  ThunderboltOutlined, SafetyCertificateOutlined,
} from '@ant-design/icons'
import { adminApi, type SecurityConfig } from '../../services/admin'
import { ApiError } from '../../services/api'

const { Text } = Typography

export default function SecuritySettings() {
  const [config, setConfig] = useState<SecurityConfig | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchConfig = useCallback(async () => {
    setLoading(true)
    try {
      const res = await adminApi.getSecurityConfig()
      setConfig(res)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '加载安全配置失败'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfig()
  }, [fetchConfig])

  if (loading && !config) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!config) {
    return <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>暂无数据</div>
  }

  // 权限表数据
  const permissionRows = Object.entries(config.rbac.roles).map(([role, perms]) => ({
    key: role,
    role: { admin: '管理员', doctor: '医生', patient: '患者' }[role] || role,
    permissions: perms,
    count: perms.length,
  }))

  const permColumns = [
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (text: string) => <Tag color={text === '管理员' ? 'red' : text === '医生' ? 'blue' : 'green'}>{text}</Tag>,
    },
    {
      title: '权限数量',
      dataIndex: 'count',
      key: 'count',
      width: 80,
    },
    {
      title: '权限列表',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (perms: string[]) => (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {perms.map(p => (
            <Tag key={p} style={{ fontSize: '11px', margin: 0 }}>{p}</Tag>
          ))}
        </div>
      ),
    },
  ]

  return (
    <div>
      {/* 安全概览 */}
      <Row gutter={[12, 12]} style={{ marginBottom: '16px' }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <SafetyCertificateOutlined style={{ fontSize: '24px', color: config.rbac.enabled ? '#16a34a' : '#94a3b8' }} />
              <div>
                <Text type="secondary" style={{ fontSize: '12px' }}>RBAC</Text>
                <div><Tag color={config.rbac.enabled ? 'success' : 'default'}>{config.rbac.enabled ? '已启用' : '未启用'}</Tag></div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ThunderboltOutlined style={{ fontSize: '24px', color: config.rate_limit.enabled ? '#16a34a' : '#94a3b8' }} />
              <div>
                <Text type="secondary" style={{ fontSize: '12px' }}>限流</Text>
                <div><Tag color={config.rate_limit.enabled ? 'success' : 'default'}>{config.rate_limit.enabled ? '已启用' : '未启用'}</Tag></div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <LockOutlined style={{ fontSize: '24px', color: config.encryption.enabled ? '#16a34a' : '#94a3b8' }} />
              <div>
                <Text type="secondary" style={{ fontSize: '12px' }}>数据加密</Text>
                <div><Tag color={config.encryption.enabled ? 'success' : 'default'}>{config.encryption.enabled ? '已启用' : '未启用'}</Tag></div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <KeyOutlined style={{ fontSize: '24px', color: '#2563eb' }} />
              <div>
                <Text type="secondary" style={{ fontSize: '12px' }}>JWT</Text>
                <div><Tag color="blue">{config.jwt.algorithm}</Tag></div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 限流配置 */}
      <Card
        title={<><ThunderboltOutlined style={{ marginRight: '8px', color: '#d97706' }} />限流配置</>}
        size="small"
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      >
        <Descriptions column={2} size="small">
          <Descriptions.Item label="限流状态">
            <Tag color={config.rate_limit.enabled ? 'success' : 'default'}>{config.rate_limit.enabled ? '启用' : '禁用'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="最大请求数">
            {config.rate_limit.max_calls} 次
          </Descriptions.Item>
          <Descriptions.Item label="时间窗口">
            {config.rate_limit.period_seconds} 秒
          </Descriptions.Item>
          <Descriptions.Item label="Redis 不可用时">
            <Tag color={config.rate_limit.fail_closed ? 'red' : 'orange'}>
              {config.rate_limit.fail_closed ? '拒绝请求' : '放行请求'}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* JWT 配置 */}
      <Card
        title={<><KeyOutlined style={{ marginRight: '8px', color: '#2563eb' }} />JWT 配置</>}
        size="small"
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      >
        <Descriptions column={2} size="small">
          <Descriptions.Item label="签名算法">{config.jwt.algorithm}</Descriptions.Item>
          <Descriptions.Item label="Access Token 有效期">
            {config.jwt.access_token_expire_minutes} 分钟
          </Descriptions.Item>
          <Descriptions.Item label="Refresh Token 有效期">
            {config.jwt.refresh_token_expire_days} 天
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 数据加密 */}
      <Card
        title={<><LockOutlined style={{ marginRight: '8px', color: '#dc2626' }} />数据加密</>}
        size="small"
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      >
        {config.encryption.enabled ? (
          <Alert
            type="success"
            message="数据加密已启用"
            description={`加密密钥${config.encryption.key_configured ? '已配置' : '未配置'} — 敏感数据使用 Fernet 对称加密保护`}
            showIcon
          />
        ) : (
          <Alert
            type="warning"
            message="数据加密未启用"
            description="建议在生产环境中配置 ENCRYPTION_KEY 并启用数据加密，保护敏感医疗信息"
            showIcon
          />
        )}
      </Card>

      {/* RBAC 权限矩阵 */}
      <Card
        title={<><SecurityScanOutlined style={{ marginRight: '8px', color: '#7c3aed' }} />RBAC 权限矩阵</>}
        size="small"
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      >
        <Table
          dataSource={permissionRows}
          columns={permColumns}
          pagination={false}
          size="small"
        />
      </Card>

      {/* 可信主机 */}
      <Card
        title="可信主机"
        size="small"
        style={{ borderRadius: '12px' }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {config.trusted_hosts.map(host => (
            <Tag key={host} color="blue">{host}</Tag>
          ))}
        </div>
      </Card>
    </div>
  )
}
