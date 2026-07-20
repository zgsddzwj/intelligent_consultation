import { useState, useCallback } from 'react'
import {
  Card, Button, Radio, Checkbox, Space, message,
  Row, Col, Typography, Divider, Alert,
} from 'antd'
import {
  ExportOutlined, FileTextOutlined, DownloadOutlined,
  DatabaseOutlined, TeamOutlined, MonitorOutlined,
} from '@ant-design/icons'

const { Text, Paragraph } = Typography

const sectionOptions = [
  { label: '用户数据', value: 'users', icon: <TeamOutlined />, desc: '用户列表、角色、状态' },
  { label: '咨询记录', value: 'consultations', icon: <FileTextOutlined />, desc: '所有咨询会话摘要' },
  { label: '知识文档', value: 'knowledge', icon: <DatabaseOutlined />, desc: '文档索引状态、大小' },
  { label: '系统信息', value: 'system', icon: <MonitorOutlined />, desc: '版本、运行时间、环境' },
]

export default function ExportReport() {
  const [format, setFormat] = useState<'json' | 'csv'>('json')
  const [sections, setSections] = useState<string[]>(['users', 'consultations', 'knowledge', 'system'])
  const [exporting, setExporting] = useState(false)

  const handleExport = useCallback(async () => {
    if (sections.length === 0) {
      message.warning('请至少选择一个导出模块')
      return
    }

    setExporting(true)
    try {
      const { adminApi } = await import('../../services/admin')
      const blob = await adminApi.exportReport({ format, sections })

      // 创建下载链接
      const url = window.URL.createObjectURL(blob as unknown as Blob)
      const link = document.createElement('a')
      link.href = url
      const ext = format === 'csv' ? 'csv' : 'json'
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      link.download = `system_report_${timestamp}.${ext}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      message.success('报告导出成功')
    } catch (err) {
      const msg = err instanceof Error ? err.message : '导出失败'
      message.error(msg)
    } finally {
      setExporting(false)
    }
  }, [format, sections])

  return (
    <div>
      <Alert
        type="info"
        message="导出系统报告"
        description="将系统数据导出为 JSON 或 CSV 格式文件，可用于数据备份、审计分析或迁移。"
        showIcon
        style={{ marginBottom: '16px', borderRadius: '12px' }}
      />

      <Row gutter={[16, 16]}>
        {/* 格式选择 */}
        <Col xs={24} lg={10}>
          <Card
            title="导出格式"
            size="small"
            style={{ borderRadius: '12px', height: '100%' }}
          >
            <Radio.Group
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
            >
              <Radio value="json">
                <Space>
                  <FileTextOutlined style={{ color: '#2563eb' }} />
                  <Text strong>JSON</Text>
                  <Text type="secondary" style={{ fontSize: '12px' }}>结构化数据，适合程序处理</Text>
                </Space>
              </Radio>
              <Radio value="csv">
                <Space>
                  <FileTextOutlined style={{ color: '#16a34a' }} />
                  <Text strong>CSV</Text>
                  <Text type="secondary" style={{ fontSize: '12px' }}>表格数据，适合 Excel 查看</Text>
                </Space>
              </Radio>
            </Radio.Group>
          </Card>
        </Col>

        {/* 内容选择 */}
        <Col xs={24} lg={14}>
          <Card
            title="导出内容"
            size="small"
            style={{ borderRadius: '12px', height: '100%' }}
          >
            <Checkbox.Group
              value={sections}
              onChange={(vals) => setSections(vals as string[])}
              style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
            >
              {sectionOptions.map(opt => (
                <Checkbox key={opt.value} value={opt.value}>
                  <Space>
                    {opt.icon}
                    <Text strong>{opt.label}</Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>{opt.desc}</Text>
                  </Space>
                </Checkbox>
              ))}
            </Checkbox.Group>
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* 导出按钮 */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
        <Button
          type="primary"
          size="large"
          icon={<DownloadOutlined />}
          loading={exporting}
          onClick={handleExport}
          style={{ borderRadius: '10px', minWidth: '160px' }}
        >
          {exporting ? '正在导出...' : `导出 ${format.toUpperCase()} 报告`}
        </Button>
        <Button
          size="large"
          icon={<ExportOutlined />}
          onClick={() => {
            setFormat('json')
            setSections(['users', 'consultations', 'knowledge', 'system'])
          }}
          style={{ borderRadius: '10px' }}
        >
          重置
        </Button>
      </div>

      {/* 导出摘要 */}
      <div style={{ marginTop: '24px', textAlign: 'center' }}>
        <Paragraph type="secondary" style={{ fontSize: '12px' }}>
          当前选择：{format.toUpperCase()} 格式 · {sections.length} 个模块 ·
          包含 {sections.map(s => sectionOptions.find(o => o.value === s)?.label).join('、')}
        </Paragraph>
      </div>
    </div>
  )
}
