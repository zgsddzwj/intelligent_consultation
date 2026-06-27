import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Select,
  Button,
  Card,
  Spin,
  message,
  Typography,
  Space,
  Tag,
  Tooltip,
  Badge,
  Row,
  Col,
  Empty,
} from 'antd'
import {
  SearchOutlined,
  ExperimentOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  ApartmentOutlined,
  NodeIndexOutlined,
  TeamOutlined,
  MedicineBoxOutlined,
  BugOutlined,
  FileSearchOutlined,
  FundOutlined,
} from '@ant-design/icons'
import ForceGraph2D from 'react-force-graph-2d'
import { useQuery } from '@tanstack/react-query'
import { knowledgeApi } from '../services/knowledge'
import type { GraphData, GraphNode } from '../services/knowledge'

const { Option } = Select
const { Text } = Typography

// 节点类型配置
interface NodeTypeConfig {
  color: string
  icon: React.ReactNode
  label: string
  description: string
}

const nodeTypeConfigs: Record<string, NodeTypeConfig> = {
  Department: { color: '#7c3aed', icon: <ApartmentOutlined />, label: '科室', description: '医疗科室分类' },
  Disease: { color: '#dc2626', icon: <MedicineBoxOutlined />, label: '疾病', description: '疾病实体' },
  Symptom: { color: '#d97706', icon: <BugOutlined />, label: '症状', description: '症状表现' },
  Drug: { color: '#2563eb', icon: <MedicineBoxOutlined />, label: '药物', description: '药品信息' },
  Examination: { color: '#16a34a', icon: <FileSearchOutlined />, label: '检查', description: '检查项目' },
}

// 统计卡片组件
function StatCard({ icon, title, value, color }: { icon: React.ReactNode; title: string; value: number | string; color: string }) {
  return (
    <Card
      size="small"
      style={{ borderRadius: '12px', border: '1px solid var(--border-color)' }}
      styles={{ body: { padding: '16px' } }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: `${color}10`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
            color: color,
            flexShrink: 0,
          }}
        >
          {icon}
        </div>
        <div>
          <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>{title}</Text>
          <Text strong style={{ fontSize: '20px', color }}>{value}</Text>
        </div>
      </div>
    </Card>
  )
}

export default function KnowledgeGraph() {
  const [selectedDepartment, setSelectedDepartment] = useState<string>('')
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(false)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const fgRef = useRef<any>(undefined)

  // 获取科室列表
  const { data: departmentsData } = useQuery({
    queryKey: ['departments'],
    queryFn: () => knowledgeApi.getDepartments(),
    staleTime: 5 * 60 * 1000,
  })

  // 获取图谱数据
  const fetchGraphData = useCallback(async (department?: string) => {
    setLoading(true)
    try {
      const response = await knowledgeApi.getGraphVisualization({
        department: department || undefined,
        depth: 2,
      })
      setGraphData(response)
    } catch (error: any) {
      message.error('加载知识图谱失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGraphData()
  }, [fetchGraphData])

  const handleSearch = useCallback(() => {
    fetchGraphData(selectedDepartment)
  }, [fetchGraphData, selectedDepartment])

  // 获取节点颜色
  const getNodeColor = (node: GraphNode): string => {
    const config = nodeTypeConfigs[node.type]
    return config?.color || '#64748b'
  }

  // 节点点击处理
  const handleNodeClick = (node: GraphNode) => {
    setSelectedNode(node)
    message.info(`已选中: ${node.label}`)
  }

  // 计算统计数据
  const stats = {
    totalNodes: graphData.nodes.length,
    totalLinks: graphData.links.length,
    types: [...new Set(graphData.nodes.map(n => n.type))].length,
  }

  return (
    <div className="page-container">
      {/* 页面标题 */}
      <div className="page-title-bar">
        <div>
          <h2>
            <ExperimentOutlined style={{ color: '#7c3aed' }} />
            医疗知识图谱
          </h2>
          <div className="subtitle">基于 Neo4j 的知识可视化与问答系统</div>
        </div>
        <Space>
          <Badge count={stats.totalNodes} overflowCount={999} style={{ backgroundColor: '#7c3aed' }} />
          <Tag color="purple">实体节点</Tag>
        </Space>
      </div>

      {/* 搜索控制栏 */}
      <Card
        size="small"
        style={{ marginBottom: '16px', borderRadius: '14px', border: '1px solid var(--border-color)' }}
        styles={{ body: { padding: '16px 20px' } }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <NodeIndexOutlined style={{ color: 'var(--primary-color)', fontSize: '15px' }} />
            <Text strong style={{ whiteSpace: 'nowrap', fontSize: '14px' }}>选择科室</Text>
            <Select
              style={{ width: 200 }}
              placeholder="请选择科室筛选"
              value={selectedDepartment || undefined}
              onChange={(val) => setSelectedDepartment(val || '')}
              allowClear
              size="large"
              showSearch
              optionFilterProp="children"
            >
              {departmentsData?.departments?.map((dept: any) => (
                <Option key={dept.name} value={dept.name}>
                  <Space>
                    <ApartmentOutlined style={{ color: '#7c3aed' }} />
                    {dept.name}
                  </Space>
                </Option>
              ))}
            </Select>
          </div>

          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            loading={loading}
            size="large"
          >
            搜索
          </Button>

          <Button
            icon={<ReloadOutlined />}
            onClick={() => { setSelectedDepartment(''); fetchGraphData() }}
            size="large"
          >
            重置
          </Button>
        </div>
      </Card>

      {/* 统计卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: '16px' }}>
        <Col xs={24} sm={8}>
          <StatCard icon={<TeamOutlined />} title="节点总数" value={stats.totalNodes} color="#2563eb" />
        </Col>
        <Col xs={24} sm={8}>
          <StatCard icon={<FundOutlined />} title="关系数量" value={stats.totalLinks} color="#0d9488" />
        </Col>
        <Col xs={24} sm={8}>
          <StatCard icon={<NodeIndexOutlined />} title="类型种类" value={stats.types} color="#d97706" />
        </Col>
      </Row>

      {/* 图谱可视化区域 */}
      <Card
        style={{ borderRadius: '14px', border: '1px solid var(--border-color)', overflow: 'hidden' }}
        styles={{ body: { padding: 0 } }}
      >
        {/* 图谱容器 */}
        <div
          style={{
            height: '520px',
            position: 'relative',
            background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
            overflow: 'hidden',
          }}
        >
          {/* 加载状态 */}
          {loading && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
                background: 'rgba(255,255,255,0.85)',
                backdropFilter: 'blur(4px)',
              }}
            >
              <Spin size="large" />
              <Text type="secondary" style={{ marginTop: '12px', fontSize: '13px' }}>
                正在加载知识图谱数据...
              </Text>
            </div>
          )}

          {/* 空状态 */}
          {!loading && graphData.nodes.length === 0 && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <span style={{ color: 'var(--text-hint)' }}>暂无图谱数据，请选择科室后搜索</span>
                }
              />
            </div>
          )}

          {/* 力导向图 */}
          {!loading && graphData.nodes.length > 0 && (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              nodeLabel={(node: any) => `${node.label}`}
              nodeColor={(node: any) => getNodeColor(node)}
              linkLabel={(link: any) => link.label || ''}
              nodeVal={(node: any) => Math.sqrt(node.properties?.length || 1) * 10 + 5}
              nodeRelSize={6}
              linkDirectionalArrowLength={6}
              linkDirectionalArrowRelPos={1}
              linkCurvature={0.25}
              linkWidth={1.5}
              linkColor={() => 'rgba(100, 116, 139, 0.2)'}
              onNodeClick={(node: any) => handleNodeClick(node)}
              onNodeHover={(node: any) => {
                document.body.style.cursor = node ? 'pointer' : 'default'
              }}
              cooldownTicks={100}
              enableZoomInteraction={true}
              enablePanInteraction={true}
              backgroundColor="transparent"
              width={undefined}
              height={undefined}
            />
          )}
        </div>

        {/* 图例区域 */}
        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid var(--border-color)',
            background: 'var(--background-white)',
          }}
        >
          <Text strong style={{ fontSize: '13px', marginBottom: '10px', display: 'block', color: 'var(--text-secondary)' }}>
            图例说明 - 节点类型
          </Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
            {Object.entries(nodeTypeConfigs).map(([type, config]) => (
              <Tooltip key={type} title={config.description}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: 'var(--radius-full)',
                    background: `${config.color}08`,
                    border: `1px solid ${config.color}20`,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      background: config.color,
                    }}
                  />
                  <span style={{ color: config.color, fontWeight: 600, fontSize: '12px' }}>
                    {config.icon} {config.label}
                  </span>
                </div>
              </Tooltip>
            ))}
          </div>

          {/* 选中节点信息 */}
          {selectedNode && (
            <div
              style={{
                marginTop: '12px',
                padding: '12px 16px',
                borderRadius: '10px',
                background: 'var(--info-bg)',
                border: '1px solid var(--primary-100)',
                animation: 'fadeIn 0.3s ease-out',
              }}
            >
              <Space align="start">
                <InfoCircleOutlined style={{ color: 'var(--primary-color)', fontSize: '15px', marginTop: '2px' }} />
                <div>
                  <Text strong style={{ fontSize: '13px' }}>当前选中</Text>
                  <div style={{ marginTop: '4px' }}>
                    <Tag color={getNodeColor(selectedNode)} style={{ fontWeight: 600 }}>
                      {selectedNode.label}
                    </Tag>
                    <Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>
                      类型: {selectedNode.type}
                    </Text>
                  </div>
                </div>
              </Space>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
