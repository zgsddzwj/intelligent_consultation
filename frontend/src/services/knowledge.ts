import api from './api'

export interface GraphVisualizationRequest {
  department?: string
  disease?: string
  depth?: number
}

export interface GraphNode {
  id: string
  label: string
  type: string
  properties?: any
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

export const knowledgeApi = {
  getGraphVisualization: (data: GraphVisualizationRequest) =>
    api.post<GraphData>('/knowledge/graph/visualization', data),
  getDepartments: () => api.get('/knowledge/graph/departments'),
  search: (query: string, top_k = 5) =>
    api.post('/knowledge/search', { query, top_k }),
}

