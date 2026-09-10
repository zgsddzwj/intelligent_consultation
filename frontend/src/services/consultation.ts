import { post, get } from './api'
import type {
  ChatRequest,
  SourceRef,
  ChatResponse,
  ChatStreamEvent,
  ConsultationHistoryItem,
  ConsultationDetail,
} from '../types/chat'

// 统一复用 types/chat 中的共享类型，避免重复维护两套相同结构
export type {
  ChatRequest,
  SourceRef,
  ChatResponse,
  ChatStreamEvent,
  ConsultationHistoryItem,
  ConsultationDetail,
}

/**
 * 流式聊天回调
 */
export interface ChatStreamCallbacks {
  /** 开始对话 */
  onStart?: (consultationId?: number) => void
  /** 思考过程 */
  onThinking?: (content: string) => void
  /** 首个token到达 */
  onFirstToken?: () => void
  /** 消息片段 */
  onMessage?: (chunk: string) => void
  /** 信息来源 */
  onSources?: (sources: SourceRef[]) => void
  /** 对话完成 */
  onDone?: (consultationId?: number) => void
  /** 发生错误 */
  onError?: (error: string) => void
}

/**
 * 流式聊天选项
 */
export interface ChatStreamOptions {
  /** AbortSignal 用于取消请求 */
  signal?: AbortSignal
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
   * 支持 AbortController 取消请求；读流空闲超过 90s 视为连接挂起自动中断
   */
  chatStream: async (
    data: ChatRequest,
    callbacks: ChatStreamCallbacks,
    options?: ChatStreamOptions
  ): Promise<void> => {
    const token = localStorage.getItem('auth_token')
    // 优先使用环境变量配置的后端地址，未配置时走同源路径（开发环境由 vite 代理转发）
    const baseURL = import.meta.env.VITE_API_BASE_URL ?? ''
    const url = `${baseURL}/api/v1/consultation/chat/stream`

    // 内部控制器：既响应调用方的 signal，也支持空闲超时自动中断
    const controller = new AbortController()
    const onExternalAbort = () => controller.abort()
    if (options?.signal) {
      if (options.signal.aborted) return
      options.signal.addEventListener('abort', onExternalAbort)
    }

    const IDLE_TIMEOUT_MS = 90_000

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(data),
        signal: controller.signal,
      })

      if (!response.ok) {
        // 401：令牌失效，清理本地状态并广播登出（与 axios 拦截器行为一致）
        if (response.status === 401) {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_user')
          window.dispatchEvent(new CustomEvent('auth:logout', { detail: { reason: 'token_expired' } }))
          callbacks.onError?.('登录已过期，请重新登录')
          return
        }
        callbacks.onError?.(
          response.status === 429 ? '请求过于频繁，请稍后再试' : `服务异常（${response.status}），请稍后重试`
        )
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        callbacks.onError?.('无法读取响应流')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      /** 读一块数据，带空闲超时；返回 null 表示超时中断 */
      const readWithTimeout = async (): Promise<ReadableStreamReadResult<Uint8Array> | null> => {
        let timer: ReturnType<typeof setTimeout> | undefined
        try {
          return await Promise.race([
            reader.read(),
            new Promise<null>((resolve) => {
              timer = setTimeout(() => resolve(null), IDLE_TIMEOUT_MS)
            }),
          ])
        } finally {
          if (timer) clearTimeout(timer)
        }
      }

      while (true) {
        const result = await readWithTimeout()
        if (result === null) {
          controller.abort()
          callbacks.onError?.('响应超时，请稍后重试')
          return
        }
        const { done, value } = result
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE 事件以空行分隔（兼容 CRLF）；单个事件内多行 data: 需拼接
        const events = buffer.split(/\r?\n\r?\n/)
        buffer = events.pop() || ''

        for (const rawEvent of events) {
          const dataLines = rawEvent
            .split(/\r?\n/)
            .filter((l) => l.startsWith('data:'))
            .map((l) => l.slice(5).replace(/^ /, ''))
          if (dataLines.length === 0) continue

          try {
            const event = JSON.parse(dataLines.join('\n')) as ChatStreamEvent

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
          } catch (e) {
            console.warn('SSE事件解析失败:', e)
          }
        }
      }
    } catch (error) {
      // AbortError 不触发 onError（属于正常取消）
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }
      callbacks.onError?.(error instanceof Error ? error.message : '网络错误')
    } finally {
      if (options?.signal) {
        options.signal.removeEventListener('abort', onExternalAbort)
      }
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
