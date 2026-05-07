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
  
  // Actions
  /** 添加消息 */
  addMessage: (message: Message) => void
  /** 设置会话ID */
  setConsultationId: (id: number) => void
  /** 清空所有消息 */
  clearMessages: () => void
  /** 删除指定消息 */
  removeMessage: (index: number) => void
  /** 设置加载状态 */
  setLoading: (loading: boolean) => void
  /** 重置整个状态 */
  reset: () => void
}

/** 初始状态 */
const initialState = {
  messages: [] as Message[],
  consultationId: null as number | null,
  isLoading: false,
}

/**
 * 咨询会话状态管理Store
 * 
 * 使用Zustand + persist中间件实现：
 * - 消息持久化（页面刷新不丢失）
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
              id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
              timestamp: new Date().toISOString(),
            },
          ],
        })),

      setConsultationId: (id) => set({ consultationId: id }),

      clearMessages: () =>
        set({
          messages: [],
          consultationId: null,
        }),

      removeMessage: (index) =>
        set((state) => ({
          messages: state.messages.filter((_, i) => i !== index),
        })),

      setLoading: (loading) => set({ isLoading: loading }),

      reset: () => set(initialState),
    }),
    {
      name: 'medical-consultation-storage',
      // 只持久化消息和会话ID，不保存loading状态
      partialize: (state) => ({
        messages: state.messages,
        consultationId: state.consultationId,
      }),
    }
  )
)
