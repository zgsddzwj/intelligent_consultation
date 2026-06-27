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
 * 流式聊天响应（含 thinking 事件）
 */
export interface ChatStreamEvent {
  type: 'start' | 'first_token' | 'message' | 'sources' | 'thinking' | 'done' | 'error'
  content?: string
  consultation_id?: number
  sources?: string[]
  error?: string
}

/**
 * 流式聊天回调
 */
export interface ChatStreamCallbacks {
  onStart?: (consultationId?: number) => void
  onThinking?: (content: string) => void
  onFirstToken?: () => void
  onMessage?: (chunk: string) => void
  onSources?: (sources: string[]) => void
  onDone?: (consultationId?: number) => void
  onError?: (error: string) => void
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
   * 流式对话（SSE POST，支持 thinking）
   * 使用 fetch + ReadableStream 解析 SSE，支持 POST body
   */
  chatStream: async (data: ChatRequest, callbacks: ChatStreamCallbacks): Promise<void> => {
    const token = localStorage.getItem('auth_token')
    const baseURL = import.meta.env.DEV ? 'http://localhost:8000' : ''
    const url = `${baseURL}/api/v1/consultation/chat/stream`

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        callbacks.onError?.(`HTTP ${response.status}`)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        callbacks.onError?.('无法读取响应流')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 解析 SSE 事件（以 data: 开头，\n\n 结尾）
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const dataMatch = line.match(/^data:\s*(.+)$/s)
          if (!dataMatch) continue

          try {
            const event = JSON.parse(dataMatch[1]) as ChatStreamEvent

            switch (event.type) {
              case 'start':
                callbacks.onStart?.(event.consultation_id)
                break
              case 'thinking':
                callbacks.onThinking?.(event.content || '')
                break
              case 'first_token':
                callbacks.onFirstToken?.()
                break
              case 'message':
                callbacks.onMessage?.(event.content || '')
                break
              case 'sources':
                callbacks.onSources?.(event.sources || [])
                break
              case 'done':
                callbacks.onDone?.(event.consultation_id)
                return
              case 'error':
                callbacks.onError?.(event.error || '未知错误')
                return
            }
          } catch {
            // 忽略解析错误
          }
        }
      }
    } catch (error) {
      callbacks.onError?.(error instanceof Error ? error.message : '网络错误')
    }
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
