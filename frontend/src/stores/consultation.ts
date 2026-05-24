import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * 消息接口定义
 */
export interface Message {
  /** 消息角色 */
  role: 'user' | 'assistant' | 'system'
  /** 消息内容 */
  content: string
  /** 信息来源引用 */
  sources?: string[]
  /** 风险等级: high | medium | low */
  risk_level?: string
  /** 消息时间戳 (ISO格式) */
  timestamp?: string
  /** 消息唯一ID */
  id?: string
  /** 是否流式输出中 */
  isStreaming?: boolean
}

/**
 * 会话状态接口
 */
interface ConsultationState {
  /** 消息列表 */
  messages: Message[]
  /** 当前会话ID */
  consultationId: number | null
  /** 是否正在加载 */
  isLoading: boolean
  /** 流式输出内容 */
  streamingContent: string
  /** 错误信息 */
  error: string | null

  // Actions
  /** 添加消息 */
  addMessage: (message: Message) => void
  /** 更新最后一条消息 */
  updateLastMessage: (updates: Partial<Message>) => void
  /** 设置会话ID */
  setConsultationId: (id: number | null) => void
  /** 清空所有消息 */
  clearMessages: () => void
  /** 删除指定消息 */
  removeMessage: (index: number) => void
  /** 设置加载状态 */
  setLoading: (loading: boolean) => void
  /** 设置流式内容 */
  setStreamingContent: (content: string) => void
  /** 追加流式内容 */
  appendStreamingContent: (chunk: string) => void
  /** 完成流式输出（将streamingContent转为正式消息） */
  finalizeStreaming: () => void
  /** 设置错误 */
  setError: (error: string | null) => void
  /** 重置整个状态 */
  reset: () => void
}

/** 初始状态 */
const initialState = {
  messages: [] as Message[],
  consultationId: null as number | null,
  isLoading: false,
  streamingContent: '',
  error: null as string | null,
}

/**
 * 咨询会话状态管理Store - 增强版
 *
 * 使用Zustand + persist中间件实现：
 * - 消息持久化（页面刷新不丢失）
 * - 流式输出状态管理
 * - 错误状态统一管理
 * - 轻量级、无Redux样板代码
 * - 完整的TypeScript类型支持
 */
export const useConsultationStore = create<ConsultationState>()(
  persist(
    (set, get) => ({
      ...initialState,

      addMessage: (message) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              ...message,
              id: message.id || `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
              timestamp: message.timestamp || new Date().toISOString(),
            },
          ],
          error: null,
        })),

      updateLastMessage: (updates) =>
        set((state) => {
          if (state.messages.length === 0) return state
          const newMessages = [...state.messages]
          const lastIndex = newMessages.length - 1
          newMessages[lastIndex] = { ...newMessages[lastIndex], ...updates }
          return { messages: newMessages }
        }),

      setConsultationId: (id) => set({ consultationId: id }),

      clearMessages: () =>
        set({
          messages: [],
          consultationId: null,
          streamingContent: '',
          error: null,
        }),

      removeMessage: (index) =>
        set((state) => ({
          messages: state.messages.filter((_, i) => i !== index),
        })),

      setLoading: (loading) => set({ isLoading: loading }),

      setStreamingContent: (content) => set({ streamingContent: content }),

      appendStreamingContent: (chunk) =>
        set((state) => ({
          streamingContent: state.streamingContent + chunk,
        })),

      finalizeStreaming: () =>
        set((state) => {
          if (!state.streamingContent.trim()) return state
          return {
            messages: [
              ...state.messages,
              {
                role: 'assistant',
                content: state.streamingContent,
                id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
                timestamp: new Date().toISOString(),
              },
            ],
            streamingContent: '',
            isLoading: false,
          }
        }),

      setError: (error) => set({ error, isLoading: false }),

      reset: () => set(initialState),
    }),
    {
      name: 'medical-consultation-storage',
      // 只持久化消息和会话ID，不保存loading/streaming/error状态
      partialize: (state) => ({
        messages: state.messages,
        consultationId: state.consultationId,
      }),
    }
  )
)
