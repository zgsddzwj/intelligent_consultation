import { post, get } from './api'
import type { ApiResponse } from './api'

/**
 * 聊天请求参数
 */
export interface ChatRequest {
  /** 用户消息内容 */
  message: string
  /** 会话ID（续聊时传入） */
  consultation_id?: number
  /** 额外上下文信息 */
  context?: Record<string, any>
  /** 用户ID */
  user_id?: number
}

/**
 * 聊天响应数据
 */
export interface ChatResponse {
  /** AI回复内容 */
  answer: string
  /** 会话ID */
  consultation_id: number
  /** 信息来源引用 */
  sources: string[]
  /** 风险等级 */
  risk_level?: string
  /** 执行耗时(ms) */
  execution_time?: number
  /** 意图识别结果 */
  intent?: string
}

/**
 * 流式聊天响应
 */
export interface ChatStreamEvent {
  type: 'start' | 'first_token' | 'message' | 'sources' | 'done' | 'error'
  content?: string
  consultation_id?: number
  sources?: string[]
  error?: string
}

/**
 * 历史记录项
 */
export interface ConsultationHistoryItem {
  id: number
  user_message: string
  assistant_response: string
  created_at: string
  status: 'active' | 'completed' | 'archived'
}

/**
 * 会话详情
 */
export interface ConsultationDetail {
  id: number
  messages: Array<{
    role: 'user' | 'assistant'
    content: string
    timestamp: string
  }>
  summary?: string
  created_at: string
  updated_at: string
}

/**
 * 反馈请求
 */
export interface FeedbackRequest {
  consultation_id: number
  trace_id?: string
  rating: number
  comment?: string
  helpful?: boolean
}

/**
 * 咨询API服务 - 增强版
 *
 * 封装所有与医疗咨询相关的API调用：
 * - 智能对话聊天
 * - 流式对话
 * - 历史记录查询
 * - 会话详情获取
 * - 用户反馈
 */
export const consultationApi = {
  /**
   * 发送消息进行AI对话
   */
  chat: (data: ChatRequest) =>
    post<ChatResponse>('/consultation/chat', data),

  /**
   * 流式对话（SSE）
   */
  chatStream: (data: ChatRequest): EventSource => {
    const params = new URLSearchParams()
    params.append('message', data.message)
    if (data.consultation_id) params.append('consultation_id', String(data.consultation_id))
    if (data.user_id) params.append('user_id', String(data.user_id))

    const token = localStorage.getItem('auth_token')
    const url = `/api/v1/consultation/chat/stream?${params.toString()}`

    return new EventSource(url, {
      withCredentials: !!token,
    })
  },

  /**
   * 获取咨询历史记录列表
   */
  getHistory: (userId?: number, limit = 10) =>
    get<ConsultationHistoryItem[]>('/consultation/history', {
      params: { user_id: userId, limit },
    }),

  /**
   * 获取单个会话详情
   */
  getDetail: (id: number) =>
    get<ConsultationDetail>(`/consultation/${id}`),

  /**
   * 结束当前会话
   */
  endSession: (consultationId: number) =>
    post(`/consultation/${consultationId}/end`),

  /**
   * 提交用户反馈
   */
  submitFeedback: (data: FeedbackRequest) =>
    post('/consultation/feedback', data),
}
