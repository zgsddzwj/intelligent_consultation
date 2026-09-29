/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 后端 API 地址（如 https://api.example.com），未配置时开发环境回退到本地 8000 端口 */
  readonly VITE_API_BASE_URL?: string
}

// ===== Web Speech API 最小类型声明 =====
// lib.dom.d.ts 已包含 SpeechRecognitionResult* 系列，但缺少控制器与事件类型，
// 这里只补充业务实际用到的成员，避免在业务代码中退化为 any。
interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number
  readonly results: SpeechRecognitionResultList
}

interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string
  readonly message: string
}

interface SpeechRecognition extends EventTarget {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  start(): void
  stop(): void
  abort(): void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognition
}

interface Window {
  SpeechRecognition?: SpeechRecognitionConstructor
  webkitSpeechRecognition?: SpeechRecognitionConstructor
}
