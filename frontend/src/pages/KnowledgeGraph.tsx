import { useState, useEffect, useRef } from 'react'
import {
  Layout,
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
  ApertureOutlined,
  NodeIndexOutlined,
  TeamOutlined,
  MedicineBoxOutlined,
  BugOutlined,
  FileSearchOutlined,
  FundOutlined,
} from '@ant-design/icons'
import ForceGraph2D from 'react-force-graph-2d'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

const { Header, Content } = Layout
const { Option } = Select
const { Title, Text, Paragraph } = Typography

// 节点类型配置
interface NodeTypeConfig {
  color: string
  icon: React.ReactNode
  label: string
  description: string
}

const nodeTypeConfigs: Record<string, NodeTypeConfig> = {
  Department: { color: '#722ed1', icon: <ApertureOutlined />, label: '科室', description: '医疗科室分类' },
  Disease: { color: '#ff4d4f', icon: <MedicineBoxOutlined />, label: '疾病', description: '疾病实体' },
  Symptom: { color: '#fa8c16', icon: <BugOutlined />, label: '症状', description: '症状表现' },
  Drug: { color: '#1890ff', icon: <MedicineBoxOutlined />, label: '药物', description: '药品信息' },
  Examination: { color: '#52c41a', icon: <FileSearchOutlined />, label: '检查', description: '检查项目' },
}

interface GraphNode {
  id: string
  label: string
  type: string
  properties?: any
}

interface GraphLink {
  source: string
  target: string
  label?: string
}

interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

// 统计卡片组件
function StatCard({ icon, title, value, color }: { icon: React.ReactNode; title: string; value: number | string; color: string }) {
  return (
    <Card
      size="small"
      style={{
        borderRadius: '16px',
        border: `1px solid ${color}20`,
        background: `${color}06`,
        transition: 'all 0.3s ease',
      }}
      bodyStyle={{ padding: '18px' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '44px',
          height: '44px',
          borderRadius: '14px',
          background: `${color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '20px',
          color: color,
        }}>
          {icon}
        </div>
        <div>
          <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>{title}</Text>
          <Text strong style={{ fontSize: '22px', color }}>{value}</Text>
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
  const fgRef = useRef<any>()

  // 获取科室列表
  const { data: departmentsData } = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get('/knowledge/graph/departments'),
  })

  // 获取图谱数据
  const fetchGraphData = async (department?: string) => {
    setLoading(true)
    try {
      const response = await api.post('/knowledge/graph/visualization', {
        department: department || null,
        depth: 2,
      })
      setGraphData(response)
    } catch (error: any) {
      message.error('加载知识图谱失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGraphData()
  }, [])

  const handleSearch = () => {
    if (selectedDepartment) {
      fetchGraphData(selectedDepartment)
    } else {
      fetchGraphData()
    }
  }

  // 获取节点颜色
  const getNodeColor = (node: GraphNode): string => {
    const config = nodeTypeConfigs[node.type]
    return config?.color || '#8c8c8c'
  }

  // 节点点击处理
  const handleNodeClick = (node: GraphNode) => {
    setSelectedNode(node)
    message.info({
      content: `选中节点: ${node.label}`,
      icon: <InfoCircleOutlined />,
    })
  }

  // 计算统计数据
  const stats = {
    totalNodes: graphData.nodes.length,
    totalLinks: graphData.links.length,
    types: [...new Set(graphData.nodes.map(n => n.type))].length,
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
            background: 'linear-gradient(135deg, #722ed1 0%, #9254de 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(114, 46, 209, 0.3)',
          }}>
            <ExperimentOutlined style={{ fontSize: '22px', color: 'white' }} />
          </div>
          <div>
            <Title level={4} style={{ margin: 0, fontWeight: 700, lineHeight: 1.3, fontSize: '17px' }}>
              医疗知识图谱
            </Title>
            <Text type="secondary" style={{ fontSize: '12px' }}>基于Neo4j的知识可视化与问答系统</Text>
          </div>
        </div>

        <Space size="small">
          <Badge count={stats.totalNodes} overflowCount={999} style={{ backgroundColor: '#722ed1' }} />
          <Tag color="purple" style={{ borderRadius: '20px', padding: '4px 14px', fontWeight: 500 }}>
            实体节点
          </Tag>
        </Space>
      </Header>

      <Content style={{ padding: '24px 32px', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
        {/* 搜索控制栏 */}
        <Card
          size="small"
          style={{
            marginBottom: '20px',
            borderRadius: '20px',
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-sm)',
          }}
          bodyStyle={{ padding: '20px 24px' }}
        >
          <Row gutter={[16, 16]} align="middle">
            <Col flex="auto">
              <Space size="large" wrap>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <NodeIndexOutlined style={{ color: 'var(--primary-color)', fontSize: '16px' }} />
                  <Text strong style={{ whiteSpace: 'nowrap' }}>选择科室</Text>
                  <Select
                    style={{ width: 220 }}
                    placeholder="请选择科室筛选"
                    value={selectedDepartment}
                    onChange={setSelectedDepartment}
                    allowClear
                    size="large"
                    showSearch
                    optionFilterProp="children"
                  >
                    {departmentsData?.departments?.map((dept: any) => (
                      <Option key={dept.name} value={dept.name}>
                        <Space>
                          <ApartmentOutlined style={{ color: '#722ed1' }} />
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
                  style={{ borderRadius: '12px', fontWeight: 600 }}
                >
                  搜索
                </Button>

                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => { setSelectedDepartment(''); fetchGraphData() }}
                  size="large"
                  style={{ borderRadius: '12px' }}
                >
                  重置
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>

        {/* 统计卡片 */}
        <Row gutter={[16, 16]} style={{ marginBottom: '20px' }}>
          <Col xs={24} sm={8}>
            <StatCard
              icon={<TeamOutlined />}
              title="节点总数"
              value={stats.totalNodes}
              color="#667eea"
            />
          </Col>
          <Col xs={24} sm={8}>
            <StatCard
              icon={<FundOutlined />}
              title="关系数量"
              value={stats.totalLinks}
              color="#10b981"
            />
          </Col>
          <Col xs={24} sm={8}>
            <StatCard
              icon={<ApertureOutlined />}
              title="类型种类"
              value={stats.types}
              color="#f59e0b"
            />
          </Col>
        </Row>

        {/* 图谱可视化区域 */}
        <Card
          style={{
            borderRadius: '20px',
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-md)',
            overflow: 'hidden',
          }}
          bodyStyle={{ padding: 0 }}
        >
          {/* 图谱容器 */}
          <div style={{
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            height: '560px',
            position: 'relative',
            background: 'linear-gradient(180deg, #fafbff 0%, #f5f0ff 100%)',
            overflow: 'hidden',
          }}>
            {/* 加载状态 */}
            {loading && (
              <div style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
                background: 'rgba(255,255,255,0.85)',
                backdropFilter: 'blur(4px)',
              }}>
                <Spin size="large" />
                <Text type="secondary" style={{ marginTop: '16px', fontSize: '14px' }}>正在加载知识图谱数据...</Text>
              </div>
            )}

            {/* 空状态 */}
            {!loading && graphData.nodes.length === 0 && (
              <div style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
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
                linkColor={() => 'rgba(102, 126, 234, 0.25)'}
                onNodeClick={(node: any) => handleNodeClick(node)}
                onNodeHover={(node: any) => {
                  document.body.style.cursor = node ? 'pointer' : 'default'
                }}
                cooldownTicks={100}
                enableZoomInteraction={true}
                enablePanInteraction={true}
                enableDragInteraction={true}
                backgroundColor="transparent"
                width={undefined}
                height={undefined}
              />
            )}
          </div>

          {/* 图例区域 */}
          <div style={{
            padding: '20px 28px',
            borderTop: '1px solid var(--border-color)',
            background: 'var(--background-warm)',
          }}>
            <Text strong style={{ fontSize: '13px', marginBottom: '12px', display: 'block', color: 'var(--text-secondary)' }}>
              📊 图例说明 - 节点类型
            </Text>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
              {Object.entries(nodeTypeConfigs).map(([type, config]) => (
                <Tooltip key={type} title={config.description}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 16px',
                      borderRadius: '20px',
                      background: `${config.color}08`,
                      border: `1px solid ${config.color}25`,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-1px)'
                      e.currentTarget.style.boxShadow = `0 2px 8px ${config.color}20`
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  >
                    <div style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: config.color,
                      boxShadow: `0 0 8px ${config.color}50`,
                    }} />
                    <span style={{ color: config.color, fontWeight: 600, fontSize: '13px' }}>
                      {config.icon} {config.label}
                    </span>
                  </div>
                </Tooltip>
              ))}
            </div>

            {/* 选中节点信息 */}
            {selectedNode && (
              <div style={{
                marginTop: '16px',
                padding: '14px 20px',
                borderRadius: '14px',
                background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.06), rgba(118, 75, 162, 0.06))',
                border: '1px solid rgba(102, 126, 234, 0.15)',
                animation: 'fadeIn 0.3s ease-out',
              }}>
                <Space align="start">
                  <InfoCircleOutlined style={{ color: 'var(--primary-color)', fontSize: '16px', marginTop: '2px' }} />
                  <div>
                    <Text strong style={{ fontSize: '14px' }}>当前选中</Text>
                    <div style={{ marginTop: '4px' }}>
                      <Tag color={getNodeColor(selectedNode)} style={{ borderRadius: '12px', fontWeight: 600 }}>
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
      </Content>
    </Layout>
  )
}

// 兼容性：Ant Design Apartment 图标
function ApartmentOutlined(props: any) {
  return <ApertureOutlined {...props} />
}
