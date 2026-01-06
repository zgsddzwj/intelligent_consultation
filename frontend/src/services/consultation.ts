import api from './api'

export interface ChatRequest {
  message: string
  consultation_id?: number
  context?: Record<string, any>
  user_id?: number
}

export interface ChatResponse {
  answer: string
  consultation_id: number
  sources: string[]
  risk_level?: string
  execution_time?: number
}

export const consultationApi = {
  chat: (data: ChatRequest) => api.post<ChatResponse>('/consultation/chat', data),
  getHistory: (user_id?: number, limit = 10) => 
    api.get('/consultation/history', { params: { user_id, limit } }),
  getDetail: (id: number) => api.get(`/consultation/${id}`),
}

