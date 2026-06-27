import { create } from 'zustand'
import { persist, subscribeWithSelector } from 'zustand/middleware'
import { devtools } from 'zustand/middleware'

/**
 * 思考步骤
 */
export interface ThinkingStep {
  content: string
  ts: number
}

/**
 * 消息接口定义
 */
export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  sources?: string[]
  risk_level?: string
  timestamp?: string
  id?: string
  isStreaming?: boolean
  thinkingSteps?: ThinkingStep[]
  isThinking?: boolean
}

/**
 * 会话状态接口 - 分层设计
 */
interface ConsultationState {
  // === 核心状态（持久化）===
  messages: Message[]
  consultationId: number | null

  // === UI状态（非持久化）===
  isLoading: boolean
  streamingContent: string
  error: string | null

  // === 派生状态（计算属性）===
  messageCount: number
  lastMessage: Message | null
  hasError: boolean
  isStreaming: boolean

  // === Actions ===
  addMessage: (message: Message) => void
  updateLastMessage: (updates: Partial<Message>) => void
  setConsultationId: (id: number | null) => void
  clearMessages: () => void
  removeMessage: (index: number) => void
  setLoading: (loading: boolean) => void
  setStreamingContent: (content: string) => void
  appendStreamingContent: (chunk: string) => void
  finalizeStreaming: () => void
  setError: (error: string | null) => void
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
 * 咨询会话状态管理Store - 极致优化版
 *
 * 架构特点：
 * - 全局状态分层（核心/UI/派生）
 * - subscribeWithSelector 精确订阅
 * - devtools 开发调试
 * - persist 智能持久化
 * - 派生状态自动计算
 */
export const useConsultationStore = create<ConsultationState>()(
  devtools(
    subscribeWithSelector(
      persist(
        (set, get) => ({
          ...initialState,

          // === 派生状态（基于get实时计算）===
          get messageCount() {
            return get().messages.length
          },
          get lastMessage() {
            const msgs = get().messages
            return msgs.length > 0 ? msgs[msgs.length - 1] : null
          },
          get hasError() {
            return get().error !== null
          },
          get isStreaming() {
            return get().streamingContent.length > 0
          },

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
            }), false, 'addMessage'),

          updateLastMessage: (updates) =>
            set((state) => {
              if (state.messages.length === 0) return state
              const newMessages = [...state.messages]
              const lastIndex = newMessages.length - 1
              newMessages[lastIndex] = { ...newMessages[lastIndex], ...updates }
              return { messages: newMessages }
            }, false, 'updateLastMessage'),

          setConsultationId: (id) => set({ consultationId: id }, false, 'setConsultationId'),

          clearMessages: () =>
            set({
              messages: [],
              consultationId: null,
              streamingContent: '',
              error: null,
            }, false, 'clearMessages'),

          removeMessage: (index) =>
            set((state) => ({
              messages: state.messages.filter((_, i) => i !== index),
            }), false, 'removeMessage'),

          setLoading: (loading) => set({ isLoading: loading }, false, 'setLoading'),

          setStreamingContent: (content) => set({ streamingContent: content }, false, 'setStreamingContent'),

          appendStreamingContent: (chunk) =>
            set((state) => ({
              streamingContent: state.streamingContent + chunk,
            }), false, 'appendStreamingContent'),

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
            }, false, 'finalizeStreaming'),

          setError: (error) => set({ error, isLoading: false }, false, 'setError'),

          reset: () => set(initialState, false, 'reset'),
        }),
        {
          name: 'medical-consultation-storage',
          // 只持久化核心状态
          partialize: (state) => ({
            messages: state.messages,
            consultationId: state.consultationId,
          }),
        }
      )
    ),
    { name: 'ConsultationStore', enabled: process.env.NODE_ENV === 'development' }
  )
)

// === 选择器函数（精确订阅，避免不必要的重渲染）===

export const selectMessages = (state: ConsultationState) => state.messages
export const selectIsLoading = (state: ConsultationState) => state.isLoading
export const selectError = (state: ConsultationState) => state.error
export const selectStreamingContent = (state: ConsultationState) => state.streamingContent
export const selectConsultationId = (state: ConsultationState) => state.consultationId
export const selectMessageCount = (state: ConsultationState) => state.messageCount
export const selectLastMessage = (state: ConsultationState) => state.lastMessage
export const selectHasError = (state: ConsultationState) => state.hasError
export const selectIsStreaming = (state: ConsultationState) => state.isStreaming

// === 便捷Hook ===

export function useMessages() {
  return useConsultationStore(selectMessages)
}

export function useIsLoading() {
  return useConsultationStore(selectIsLoading)
}

export function useLastMessage() {
  return useConsultationStore(selectLastMessage)
}
