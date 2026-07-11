import { useState, useRef, useCallback, useEffect } from 'react'

/** 录音 Hook 返回值 */
interface UseAudioRecorderReturn {
  /** 是否正在录音 */
  isRecording: boolean
  /** 录音完成后的音频 Blob */
  audioBlob: Blob | null
  /** 开始录音 */
  startRecording: () => Promise<void>
  /** 停止录音 */
  stopRecording: () => void
  /** 取消录音（不生成音频） */
  cancelRecording: () => void
  /** 录音时长（秒） */
  recordingTime: number
  /** 错误信息 */
  error: string | null
}

/** 最大录音时长（秒） */
const MAX_RECORDING_DURATION = 60

/**
 * 音频录制 Hook
 *
 * 使用浏览器 MediaRecorder API 录制音频，返回 Blob 供后端 ASR 识别。
 * 自动处理麦克风权限、录音超时、资源清理。
 */
export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [recordingTime, setRecordingTime] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<number | null>(null)
  const cancelledRef = useRef(false)

  const startRecording = useCallback(async () => {
    try {
      setError(null)
      setAudioBlob(null)
      setRecordingTime(0)
      cancelledRef.current = false

      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // 选择支持的音频格式
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : ''

      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)

      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = () => {
        if (cancelledRef.current) {
          // 取消录音，不生成音频
          setAudioBlob(null)
        } else {
          const blob = new Blob(chunksRef.current, {
            type: mimeType || 'audio/webm',
          })
          setAudioBlob(blob)
        }
        // 释放麦克风
        streamRef.current?.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }

      mediaRecorder.start()
      setIsRecording(true)

      // 录音计时
      timerRef.current = window.setInterval(() => {
        setRecordingTime((prev) => {
          const next = prev + 1
          if (next >= MAX_RECORDING_DURATION) {
            // 达到最大时长，自动停止
            stopRecording()
          }
          return next
        })
      }, 1000)
    } catch (err) {
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        setError('麦克风权限被拒绝，请在浏览器设置中允许使用麦克风')
      } else if (err instanceof DOMException && err.name === 'NotFoundError') {
        setError('未找到麦克风设备，请检查设备连接')
      } else {
        setError('无法启动录音，请稍后重试')
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const cancelRecording = useCallback(() => {
    cancelledRef.current = true
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  // 组件卸载时清理资源
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  return {
    isRecording,
    audioBlob,
    startRecording,
    stopRecording,
    cancelRecording,
    recordingTime,
    error,
  }
}
