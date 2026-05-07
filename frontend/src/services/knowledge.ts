import api from './api'

/**
 * 图谱可视化请求参数
 */
export interface GraphVisualizationRequest {
  /** 科室筛选 */
  department?: string
  /** 疾病筛选 */
  disease?: string
  /** 搜索深度，默认2 */
  depth?: number
}

/**
 * 知识图谱节点
 */
export interface GraphNode {
  /** 节点ID */
  id: string
  /** 节点标签/名称 */
  label: string
  /** 节点类型 (Department/Disease/Symptom/Drug/Examination) */
  type: string
  /** 节点属性 */
  properties?: Record<string, any>
}

/**
 * 知识图谱关系边
 */
export interface GraphLink {
  /** 起始节点ID */
  source: string | GraphNode
  /** 目标节点ID */
  target: string | GraphNode
  /** 关系标签 */
  label?: string
}

/**
 * 图谱数据（完整图结构）
 */
export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

/**
 * 搜索结果项
 */
export interface SearchResult {
  id: string
  title: string
  content: string
  source: string
  score: number
  highlights?: string[]
}

/**
 * 科室信息
 */
export interface DepartmentInfo {
  name: string
  description?: string
  nodeCount?: number
}

/**
 * 知识库API服务
 * 
 * 封装所有与知识图谱和知识检索相关的API调用：
 * - 图谱数据可视化
 * - 科室列表查询
 * - 全文搜索
 */
export const knowledgeApi = {
  /**
   * 获取知识图谱可视化数据
   * @param params 可视化请求参数
   * @returns 图谱数据（节点+边）
   */
  getGraphVisualization: (params: GraphVisualizationRequest) =>
    api.post<GraphData>('/knowledge/graph/visualization', params),

  /**
   * 获取科室列表
   * @returns 科室信息数组
   */
  getDepartments: () =>
    api.get<DepartmentInfo[]>('/knowledge/graph/departments'),

  /**
   * 知识库全文搜索
   * @param query 搜索关键词
   * @param topK 返回数量，默认5
   * @returns 搜索结果列表
   */
  search: (query: string, topK = 5) =>
    api.post<SearchResult[]>('/knowledge/search', { query, top_k: topK }),

  /**
   * 获取实体详情
   * @param entityId 实体ID
   * @returns 完整实体信息及关联关系
   */
  getEntityDetail: (entityId: string) =>
    api.get(`/knowledge/entity/${entityId}`),

  /**
   * 获取实体关联路径
   * @param sourceId 起始实体ID
   * @param targetId 目标实体ID
   * @param maxDepth 最大深度，默认3
   * @returns 关联路径列表
   */
  getEntityPath: (
    sourceId: string,
    targetId: string,
    maxDepth = 3
  ) =>
    api.post('/knowledge/path', {
      source_id: sourceId,
      target_id: targetId,
      max_depth: maxDepth,
    }),
}
