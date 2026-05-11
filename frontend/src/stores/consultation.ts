import { create } from 'zustand'
import type { Message } from '../types/chat'

interface ConsultationState {
  messages: Message[]
  consultationId: number | null
  addMessage: (message: Message) => void
  setConsultationId: (id: number | null) => void
  clearMessages: () => void
}

export const useConsultationStore = create<ConsultationState>((set) => ({
  messages: [],
  consultationId: null,
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, { ...message, timestamp: new Date().toISOString() }],
    })),
  setConsultationId: (id) => set({ consultationId: id }),
  clearMessages: () => set({ messages: [], consultationId: null }),
}))
