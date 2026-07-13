import { useState, useRef, useCallback, useEffect, useMemo } from 'react'

/** SpeechRecognition 返回值 */
interface UseSpeechRecognitionReturn {
  /** 是否正在识别 */
  isListening: boolean
  /** 实时识别的临时文本 */
  interimTranscript: string
  /** 最终识别的文本 */
  finalTranscript: string
  /** 错误信息 */
  error: string | null
  /** 是否支持 Web Speech API */
  isSupported: boolean
  /** 开始识别 */
  startListening: () => void
  /** 停止识别 */
  stopListening: () => void
  /** 取消识别（清除已识别内容） */
  resetTranscript: () => void
}

/**
 * 语音识别 Hook（基于浏览器 Web Speech API）
 *
 * 优势：
 * - 无需后端依赖，Chrome/Edge/Safari 原生支持
 * - 实时返回中间结果，用户体验好
 * - 免费无限制
 *
 * 注意：
 * - Chrome 需要联网（使用 Google 语音服务）
 * - 需要用户授权麦克风权限
 */
export function useSpeechRecognition(lang: string = 'zh-CN'): UseSpeechRecognitionReturn {
  const [isListening, setIsListening] = useState(false)
  const [interimTranscript, setInterimTranscript] = useState('')
  const [finalTranscript, setFinalTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)

  const recognitionRef = useRef<any>(null)

  // 检测浏览器是否支持 Web Speech API（只计算一次）
  const SpeechRecognitionClass = useMemo(
    () =>
      typeof window !== 'undefined'
        ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
        : null,
    []
  )

  const isSupported = !!SpeechRecognitionClass

  // 初始化 SpeechRecognition 实例
  const initRecognition = useCallback(() => {
    if (!SpeechRecognitionClass) return null

    const recognition = new SpeechRecognitionClass()
    recognition.lang = lang
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onresult = (event: any) => {
      let interim = ''
      let final = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          final += transcript
        } else {
          interim += transcript
        }
      }

      if (final) {
        setFinalTranscript((prev) => prev + final)
      }
      setInterimTranscript(interim)
    }

    recognition.onerror = (event: any) => {
      let msg = '语音识别失败'
      switch (event.error) {
        case 'no-speech':
          msg = '未检测到语音，请重试'
          break
        case 'audio-capture':
          msg = '无法访问麦克风，请检查设备'
          break
        case 'not-allowed':
          msg = '麦克风权限被拒绝，请在浏览器设置中允许'
          break
        case 'network':
          msg = '网络错误，语音识别需要联网'
          break
        case 'aborted':
          // 用户主动取消，不提示错误
          return
        default:
          msg = `语音识别错误: ${event.error}`
      }
      setError(msg)
    }

    recognition.onend = () => {
      setIsListening(false)
      setInterimTranscript('')
    }

    return recognition
  }, [SpeechRecognitionClass, lang])

  const startListening = useCallback(() => {
    setError(null)
    setInterimTranscript('')
    setFinalTranscript('')

    if (!SpeechRecognitionClass) {
      setError('当前浏览器不支持语音识别，请使用 Chrome、Edge 或 Safari')
      return
    }

    // 复用已有实例或创建新的
    if (!recognitionRef.current) {
      recognitionRef.current = initRecognition()
    }

    const recognition = recognitionRef.current
    if (!recognition) return

    try {
      recognition.start()
      setIsListening(true)
    } catch {
      // 可能上一次识别还未完全停止，重试一次
      try {
        recognition.stop()
        setTimeout(() => {
          recognition.start()
          setIsListening(true)
        }, 200)
      } catch {
        setError('无法启动语音识别，请刷新页面重试')
      }
    }
  }, [SpeechRecognitionClass, initRecognition])

  const stopListening = useCallback(() => {
    const recognition = recognitionRef.current
    if (recognition && isListening) {
      try {
        recognition.stop()
      } catch {
        // 忽略停止错误
      }
      setIsListening(false)
    }
  }, [isListening])

  const resetTranscript = useCallback(() => {
    setFinalTranscript('')
    setInterimTranscript('')
    setError(null)
  }, [])

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch {
          // 忽略
        }
      }
    }
  }, [])

  return {
    isListening,
    interimTranscript,
    finalTranscript,
    error,
    isSupported,
    startListening,
    stopListening,
    resetTranscript,
  }
}
