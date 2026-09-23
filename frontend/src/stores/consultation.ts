import { create } from 'zustand'
import { persist, subscribeWithSelector } from 'zustand/middleware'
import { devtools } from 'zustand/middleware'
import type { Message } from '../types/chat'

// 统一复用 types/chat 中的共享类型，避免重复维护两套相同结构
export type { Message }

/**
 * 会话状态接口
 *
 * 流式输出由 PatientPortal 的本地 state 驱动渲染，store 只负责
 * 持久化的核心会话数据（消息列表与咨询ID）。
 */
interface ConsultationState {
  messages: Message[]
  consultationId: number | null

  addMessage: (message: Message) => void
  updateLastMessage: (updates: Partial<Message>) => void
  setConsultationId: (id: number | null) => void
  clearMessages: () => void
}

/**
 * 咨询会话状态管理Store
 */
export const useConsultationStore = create<ConsultationState>()(
  devtools(
    subscribeWithSelector(
      persist(
        (set) => ({
          messages: [],
          consultationId: null,

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
            }, false, 'clearMessages'),
        }),
        {
          name: 'medical-consultation-storage',
          // 只持久化核心状态
          partialize: (state) => ({
            messages: state.messages,
            consultationId: state.consultationId,
          }),
          // 恢复时清理流式瞬态标志，避免刷新后消息永久卡在"思考中"
          onRehydrateStorage: () => (state) => {
            state?.messages?.forEach((m) => {
              m.isStreaming = false
              m.isThinking = false
            })
          },
        }
      )
    ),
    { name: 'ConsultationStore', enabled: import.meta.env.DEV }
  )
)
