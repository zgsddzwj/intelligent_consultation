import { post, get } from './api'

export interface GraphVisualizationRequest {
  department?: string
  disease?: string
  depth?: number
}

export interface GraphNode {
  id: string
  label: string
  type: string
  properties?: Record<string, unknown>
}

export interface GraphLink {
  source: string
  target: string
  label?: string
}

export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface DepartmentItem {
  name: string
  description?: string
}

export interface SearchResultItem {
  id: string | number
  text: string
  score: number
  source?: string
}

export const knowledgeApi = {
  /** 获取知识图谱可视化数据 */
  getGraphVisualization: (data: GraphVisualizationRequest) =>
    post<GraphData>('/knowledge/graph/visualization', data),

  /** 获取科室列表 */
  getDepartments: () =>
    get<{ departments: DepartmentItem[] }>('/knowledge/graph/departments'),

  /** 知识库搜索 */
  search: (query: string, top_k = 5) =>
    post<{ results: SearchResultItem[] }>('/knowledge/search', { query, top_k }),
}
