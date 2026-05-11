import { create } from 'zustand'
import type { Message } from '../types/chat'

interface ConsultationState {
  messages: Message[]
  consultationId: number | null
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  setConsultationId: (id: number | null) => void
  clearMessages: () => void
}

/** 生成唯一消息ID */
function generateMessageId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

export const useConsultationStore = create<ConsultationState>((set) => ({
  messages: [],
  consultationId: null,
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: generateMessageId(),
          timestamp: new Date().toISOString(),
        },
      ],
    })),
  setConsultationId: (id) => set({ consultationId: id }),
  clearMessages: () => set({ messages: [], consultationId: null }),
}))
