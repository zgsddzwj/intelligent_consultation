import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Layout, Select, Button, Card, Spin, message } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import ForceGraph2D from 'react-force-graph-2d'
import { useQuery } from '@tanstack/react-query'
import { knowledgeApi } from '../services/knowledge'
import type { GraphData, GraphNode } from '../services/knowledge'

const { Header, Content } = Layout
const { Option } = Select

/** 根据节点类型返回对应颜色 */
function getNodeColor(node: GraphNode): string {
  const typeColors: Record<string, string> = {
    Department: '#722ed1',
    Disease: '#ff4d4f',
    Symptom: '#fa8c16',
    Drug: '#1890ff',
    Examination: '#52c41a',
  }
  return typeColors[node.type] || '#8c8c8c'
}

export default function KnowledgeGraph() {
  const [selectedDepartment, setSelectedDepartment] = useState<string>('')
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(false)
  const fgRef = useRef<unknown>(null)

  // 获取科室列表
  const { data: departmentsData } = useQuery({
    queryKey: ['departments'],
    queryFn: () => knowledgeApi.getDepartments(),
    staleTime: 5 * 60 * 1000, // 5分钟缓存
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

  // 缓存图例数据，避免重复创建
  const legendItems = useMemo(() => [
    { color: '#722ed1', label: '科室' },
    { color: '#ff4d4f', label: '疾病' },
    { color: '#fa8c16', label: '症状' },
    { color: '#1890ff', label: '药物' },
    { color: '#52c41a', label: '检查' },
  ], [])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
        <h1 style={{ margin: 0, lineHeight: '64px' }}>
          基于知识图谱的医疗知识可视化与问答系统
        </h1>
      </Header>
      <Content style={{ padding: '24px' }}>
        <Card>
          <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span>选择科室:</span>
            <Select
              style={{ width: 200 }}
              placeholder="请选择科室"
              value={selectedDepartment}
              onChange={setSelectedDepartment}
              allowClear
            >
              {departmentsData?.departments?.map((dept) => (
                <Option key={dept.name} value={dept.name}>
                  {dept.name}
                </Option>
              ))}
            </Select>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSearch}
              loading={loading}
            >
              搜索
            </Button>
          </div>

          <div style={{ border: '1px solid #f0f0f0', borderRadius: '4px', height: '600px' }}>
            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <Spin size="large" />
              </div>
            ) : (
              <ForceGraph2D
                ref={fgRef as React.RefObject<never>}
                graphData={graphData}
                nodeLabel={(node: GraphNode) => `${node.label} (${node.type})`}
                nodeColor={(node: GraphNode) => getNodeColor(node)}
                linkLabel={(link: { label?: string }) => link.label || ''}
                nodeVal={(node: GraphNode) => Math.sqrt((node.properties?.length as number) || 1) * 10}
                linkDirectionalArrowLength={6}
                linkDirectionalArrowRelPos={1}
                linkCurvature={0.25}
                onNodeClick={(node: GraphNode) => {
                  message.info(`节点: ${node.label}, 类型: ${node.type}`)
                }}
                // 性能优化：限制节点和边的绘制质量以提升大数据量性能
                warmupTicks={10}
                cooldownTicks={50}
              />
            )}
          </div>

          <div style={{ marginTop: '16px', fontSize: '12px', color: '#8c8c8c' }}>
            <div>图例:</div>
            <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
              {legendItems.map((item) => (
                <span key={item.label}>
                  <span style={{ color: item.color }}>■</span> {item.label}
                </span>
              ))}
            </div>
          </div>
        </Card>
      </Content>
    </Layout>
  )
}
