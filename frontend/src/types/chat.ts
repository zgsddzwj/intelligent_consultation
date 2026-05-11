/** 聊天消息角色 */
export type MessageRole = 'user' | 'assistant'

/** 单条聊天消息 */
export interface Message {
  id: string
  role: MessageRole
  content: string
  sources?: string[]
  risk_level?: string
  timestamp?: string
}

/** 聊天请求参数 */
export interface ChatRequest {
  message: string
  consultation_id?: number
  context?: Record<string, unknown>
  user_id?: number
}

/** 聊天响应数据 */
export interface ChatResponse {
  answer: string
  consultation_id: number
  sources: string[]
  risk_level?: string
  execution_time?: number
}

/** 风险等级 */
export type RiskLevel = 'high' | 'medium' | 'low'

/** 图片分析响应 */
export interface ImageAnalysisResponse {
  analysis_result: string
  medical_terms: string[]
}
