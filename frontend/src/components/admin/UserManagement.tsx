import { useState, useCallback, useEffect } from 'react'
import {
  Table, Button, Tag, Space, Input, Select, Modal, message,
  Popconfirm, Tooltip, Switch, Row, Col, Card, Statistic,
} from 'antd'
import {
  UserOutlined, SearchOutlined, DeleteOutlined,
  ReloadOutlined, TeamOutlined, CheckCircleOutlined, StopOutlined,
} from '@ant-design/icons'
import { adminApi, type AdminUser } from '../../services/admin'
import { ApiError } from '../../services/api'

const { Option } = Select

const roleConfig: Record<string, { label: string; color: string }> = {
  admin: { label: '管理员', color: 'red' },
  doctor: { label: '医生', color: 'blue' },
  patient: { label: '患者', color: 'green' },
}

export default function UserManagement() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [roleFilter, setRoleFilter] = useState<string>('')
  const [keyword, setKeyword] = useState('')
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)
  const [editRole, setEditRole] = useState<string>('patient')
  const [editActive, setEditActive] = useState(true)
  const [editFullName, setEditFullName] = useState('')

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await adminApi.getUsers({
        page,
        page_size: pageSize,
        role: roleFilter || undefined,
        keyword: keyword || undefined,
      })
      setUsers(res.users || [])
      setTotal(res.total)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '加载用户列表失败'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, roleFilter, keyword])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const handleSearch = useCallback(() => {
    setPage(1)
    fetchUsers()
  }, [fetchUsers])

  const handleEdit = useCallback((user: AdminUser) => {
    setEditingUser(user)
    setEditRole(user.role)
    setEditActive(user.is_active)
    setEditFullName(user.full_name || '')
    setEditModalVisible(true)
  }, [])

  const handleSaveEdit = useCallback(async () => {
    if (!editingUser) return
    try {
      await adminApi.updateUser(editingUser.id, {
        role: editRole,
        is_active: editActive,
        full_name: editFullName || undefined,
      })
      message.success('用户更新成功')
      setEditModalVisible(false)
      fetchUsers()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '更新失败'
      message.error(msg)
    }
  }, [editingUser, editRole, editActive, editFullName, fetchUsers])

  const handleDelete = useCallback(async (userId: number) => {
    try {
      await adminApi.deleteUser(userId)
      message.success('用户删除成功')
      fetchUsers()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '删除失败'
      message.error(msg)
    }
  }, [fetchUsers])

  const handleBatchAction = useCallback(async (action: 'activate' | 'deactivate' | 'delete') => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择用户')
      return
    }
    const actionText = { activate: '启用', deactivate: '禁用', delete: '删除' }[action]
    try {
      await adminApi.batchActionUsers(selectedRowKeys, action)
      message.success(`批量${actionText}成功`)
      setSelectedRowKeys([])
      fetchUsers()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : `批量${actionText}失败`
      message.error(msg)
    }
  }, [selectedRowKeys, fetchUsers])

  const handleToggleActive = useCallback(async (user: AdminUser) => {
    try {
      await adminApi.updateUser(user.id, { is_active: !user.is_active })
      message.success(`用户已${!user.is_active ? '启用' : '禁用'}`)
      fetchUsers()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '操作失败'
      message.error(msg)
    }
  }, [fetchUsers])

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (text: string) => <span style={{ fontWeight: 600 }}>{text}</span>,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (role: string) => {
        const cfg = roleConfig[role] || { label: role, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean, record: AdminUser) => (
        <Switch
          checked={active}
          size="small"
          onChange={() => handleToggleActive(record)}
        />
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (ts: string) => ts
        ? new Date(ts).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
        : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: AdminUser) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button type="link" size="small" onClick={() => handleEdit(record)}>
              编辑
            </Button>
          </Tooltip>
          <Popconfirm
            title="确认删除该用户？"
            description="此操作不可恢复"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const activeCount = users.filter(u => u.is_active).length

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: '16px' }}>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <Statistic title="总用户数" value={total} prefix={<TeamOutlined />} valueStyle={{ fontSize: '20px' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <Statistic title="本页活跃" value={activeCount} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#16a34a', fontSize: '20px' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <Statistic title="本页禁用" value={users.length - activeCount} prefix={<StopOutlined />} valueStyle={{ color: '#dc2626', fontSize: '20px' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderRadius: '12px' }}>
            <Statistic title="当前页" value={`${page}/${Math.ceil(total / pageSize) || 1}`} valueStyle={{ fontSize: '20px' }} />
          </Card>
        </Col>
      </Row>

      {/* 搜索筛选栏 */}
      <div style={{ marginBottom: '16px', display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
        <Input
          placeholder="搜索用户名/邮箱"
          prefix={<SearchOutlined />}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 240 }}
          allowClear
        />
        <Select
          placeholder="角色筛选"
          value={roleFilter || undefined}
          onChange={(val) => setRoleFilter(val || '')}
          allowClear
          style={{ width: 120 }}
        >
          <Option value="admin">管理员</Option>
          <Option value="doctor">医生</Option>
          <Option value="patient">患者</Option>
        </Select>
        <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
          搜索
        </Button>
        <Button icon={<ReloadOutlined />} onClick={() => { setKeyword(''); setRoleFilter(''); setPage(1); fetchUsers() }}>
          重置
        </Button>
        {selectedRowKeys.length > 0 && (
          <Space>
            <span style={{ fontSize: '13px', color: '#64748b' }}>已选 {selectedRowKeys.length} 项</span>
            <Button size="small" icon={<CheckCircleOutlined />} onClick={() => handleBatchAction('activate')}>
              批量启用
            </Button>
            <Button size="small" icon={<StopOutlined />} onClick={() => handleBatchAction('deactivate')}>
              批量禁用
            </Button>
            <Popconfirm title="确认批量删除？" onConfirm={() => handleBatchAction('delete')} okText="确认" cancelText="取消" okButtonProps={{ danger: true }}>
              <Button size="small" danger icon={<DeleteOutlined />}>
                批量删除
              </Button>
            </Popconfirm>
          </Space>
        )}
      </div>

      {/* 用户表格 */}
      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="middle"
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as number[]),
        }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />

      {/* 编辑弹窗 */}
      <Modal
        title={`编辑用户 — ${editingUser?.username || ''}`}
        open={editModalVisible}
        onOk={handleSaveEdit}
        onCancel={() => setEditModalVisible(false)}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '16px 0' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>角色</label>
            <Select value={editRole} onChange={setEditRole} style={{ width: '100%' }}>
              <Option value="admin">管理员</Option>
              <Option value="doctor">医生</Option>
              <Option value="patient">患者</Option>
            </Select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>姓名</label>
            <Input value={editFullName} onChange={(e) => setEditFullName(e.target.value)} placeholder="输入姓名（可选）" />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 600, fontSize: '13px' }}>账号状态</label>
            <Switch checked={editActive} onChange={setEditActive} checkedChildren="启用" unCheckedChildren="禁用" />
          </div>
        </div>
      </Modal>
    </div>
  )
}
