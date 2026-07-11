import { post } from './api'

/** ASR 语音识别响应 */
export interface ASRResponse {
  /** 识别出的文本 */
  text: string
  /** 置信度 */
  confidence: number
}

/** TTS 语音合成响应 */
export interface TTSResponse {
  /** 音频文件 URL */
  audio_url: string
  /** 音频时长（秒） */
  duration: number
}

/**
 * 语音 API 服务
 *
 * 封装 ASR 语音识别和 TTS 语音合成的 API 调用
 */
export const speechApi = {
  /**
   * 语音转文字 (ASR)
   * 上传音频文件，返回识别文本
   */
  asr: async (audioBlob: Blob): Promise<ASRResponse> => {
    const formData = new FormData()
    formData.append('audio_file', audioBlob, 'recording.webm')
    formData.append('language', 'zh')

    return post<ASRResponse>('/speech/asr', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000, // ASR 需要更长的超时
    })
  },

  /**
   * 文字转语音 (TTS)
   * 输入文本，返回音频文件 URL
   */
  tts: async (text: string, voice?: string): Promise<TTSResponse> => {
    return post<TTSResponse>('/speech/tts', {
      text,
      voice,
    })
  },
}
