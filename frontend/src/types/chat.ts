/** 聊天消息角色 */
export type MessageRole = 'user' | 'assistant' | 'system'

/** 风险等级 */
export type RiskLevel = 'high' | 'medium' | 'low'

/** 消息状态 */
export type MessageStatus = 'sending' | 'sent' | 'error' | 'streaming'

/** 思考步骤 */
export interface ThinkingStep {
  /** 步骤内容 */
  content: string
  /** 时间戳 */
  ts: number
}

/** 单条聊天消息 */
export interface Message {
  /** 消息唯一ID */
  id?: string
  /** 消息角色 */
  role: MessageRole
  /** 消息内容 */
  content: string
  /** 信息来源引用 */
  sources?: string[]
  /** 风险等级 */
  risk_level?: RiskLevel
  /** 消息时间戳 (ISO格式) */
  timestamp?: string
  /** 消息状态 */
  status?: MessageStatus
  /** 是否流式输出中 */
  isStreaming?: boolean
  /** 思考过程步骤 */
  thinkingSteps?: ThinkingStep[]
  /** 是否正在思考 */
  isThinking?: boolean
}

/** 聊天请求参数 */
export interface ChatRequest {
  /** 用户消息内容 */
  message: string
  /** 会话ID（续聊时传入） */
  consultation_id?: number
  /** 额外上下文信息 */
  context?: Record<string, unknown>
  /** 用户ID */
  user_id?: number
}

/** 聊天响应数据 */
export interface ChatResponse {
  /** AI回复内容 */
  answer: string
  /** 会话ID */
  consultation_id: number
  /** 信息来源引用 */
  sources: string[]
  /** 风险等级 */
  risk_level?: RiskLevel
  /** 执行耗时(ms) */
  execution_time?: number
  /** 意图识别结果 */
  intent?: string
}

/** 流式聊天事件 */
export interface ChatStreamEvent {
  /** 事件类型 */
  type: 'start' | 'first_token' | 'message' | 'sources' | 'thinking' | 'done' | 'error'
  /** 内容片段 */
  content?: string
  /** 会话ID */
  consultation_id?: number
  /** 信息来源 */
  sources?: string[]
  /** 错误信息 */
  error?: string
}

/** 图片分析响应 */
export interface ImageAnalysisResponse {
  /** 分析结果 */
  analysis_result: string
  /** 识别出的医疗术语 */
  medical_terms: string[]
  /** 置信度 */
  confidence?: number
}

/** 咨询历史记录项 */
export interface ConsultationHistoryItem {
  /** 记录ID */
  id: number
  /** 用户消息 */
  user_message: string
  /** AI回复 */
  assistant_response: string
  /** 创建时间 */
  created_at: string
  /** 状态 */
  status: 'active' | 'completed' | 'archived'
}

/** 会话详情 */
export interface ConsultationDetail {
  /** 会话ID */
  id: number
  /** 消息列表 */
  messages: Array<{
    role: MessageRole
    content: string
    timestamp: string
  }>
  /** 会话摘要 */
  summary?: string
  /** 创建时间 */
  created_at: string
  /** 更新时间 */
  updated_at: string
}

/** 用户反馈 */
export interface UserFeedback {
  /** 会话ID */
  consultation_id: number
  /** 追踪ID */
  trace_id?: string
  /** 评分 1-5 */
  rating: number
  /** 评论 */
  comment?: string
  /** 是否有帮助 */
  helpful?: boolean
}

/** API统一响应格式 */
export interface ApiResponse<T = unknown> {
  /** 是否成功 */
  success: boolean
  /** 响应数据 */
  data: T
  /** 提示消息 */
  message?: string
  /** 错误信息 */
  error?: {
    /** 错误码 */
    code: string
    /** 错误消息 */
    message: string
    /** 错误详情 */
    details?: Record<string, unknown>
    /** 请求ID */
    request_id?: string
  }
}

/** 分页参数 */
export interface PaginationParams {
  /** 页码 */
  page?: number
  /** 每页数量 */
  page_size?: number
  /** 排序字段 */
  order_by?: string
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  /** 数据列表 */
  items: T[]
  /** 总数量 */
  total: number
  /** 当前页 */
  page: number
  /** 每页数量 */
  page_size: number
  /** 总页数 */
  total_pages: number
}
