import { post, get } from './api'

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
 * 咨询API服务
 * 
 * 封装所有与医疗咨询相关的API调用：
 * - 智能对话聊天
 * - 历史记录查询
 * - 会话详情获取
 */
export const consultationApi = {
  /**
   * 发送消息进行AI对话
   * @param data 聊天请求参数
   * @returns AI回复数据
   */
  chat: (data: ChatRequest) =>
    api.post<ChatResponse>('/consultation/chat', data),

  /**
   * 获取咨询历史记录列表
   * @param userId 用户ID (可选)
   * @param limit 返回数量限制，默认10
   * @returns 历史记录列表
   */
  getHistory: (userId?: number, limit = 10) =>
    api.get<ConsultationHistoryItem[]>('/consultation/history', {
      params: { user_id: userId, limit },
    }),

  /**
   * 获取单个会话详情
   * @param id 会话ID
   * @returns 会话详情（包含完整消息记录）
   */
  getDetail: (id: number) =>
    api.get<ConsultationDetail>(`/consultation/${id}`),

  /**
   * 结束当前会话
   * @param consultationId 会话ID
   */
  endSession: (consultationId: number) =>
    api.post(`/consultation/${consultationId}/end`),

  /**
   * 对会话进行评分反馈
   * @param consultationId 会话ID
   * @param score 评分 (1-5)
   * @param feedback 反馈文字 (可选)
   */
  submitFeedback: (
    consultationId: number,
    score: number,
    feedback?: string
  ) =>
    api.post(`/consultation/${consultationId}/feedback`, {
      score,
      feedback,
    }),
}
