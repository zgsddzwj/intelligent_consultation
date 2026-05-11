import { post, get } from './api'

export interface ChatRequest {
  message: string
  consultation_id?: number
  context?: Record<string, unknown>
  user_id?: number
}

export interface ChatResponseData {
  answer: string
  consultation_id: number
  sources: string[]
  risk_level?: string
  execution_time?: number
}

export interface ConsultationHistoryItem {
  id: number
  user_id: number
  message: string
  response: string
  created_at: string
}

export const consultationApi = {
  /** 发送聊天消息 */
  chat: (data: ChatRequest) =>
    post<{ data: ChatResponseData }>('/consultation/chat', data),

  /** 获取咨询历史 */
  getHistory: (user_id?: number, limit = 10) =>
    get<{ data: ConsultationHistoryItem[] }>('/consultation/history', {
      params: { user_id, limit },
    }),

  /** 获取咨询详情 */
  getDetail: (id: number) =>
    get<{ data: ConsultationHistoryItem }>(`/consultation/${id}`),
}
