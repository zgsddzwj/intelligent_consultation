import { useState, useRef, useCallback } from 'react'
import { Button, Tooltip, message } from 'antd'
import { SoundOutlined, PauseOutlined, LoadingOutlined } from '@ant-design/icons'
import { speechApi } from '../../services/speech'

interface VoicePlayerProps {
  /** 待播放的文本内容 */
  text: string
  /** 消息唯一标识（用于缓存键，可选） */
  messageId?: string
}

/**
 * 语音播放组件
 *
 * 点击播放按钮，将文本发送到后端 TTS 服务（Edge-TTS）合成语音并播放。
 * 支持播放/暂停切换，首次播放会请求后端合成，之后使用缓存的音频 URL。
 *
 * 后端使用 Edge-TTS（免费、无需 API Key、140+ 中文音色）
 */
export default function VoicePlayer({ text }: VoicePlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handlePlay = useCallback(async () => {
    // 如果已有音频 URL，直接播放/暂停切换
    if (audioUrl && audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause()
      } else {
        try {
          await audioRef.current.play()
        } catch {
          // play() 可能因用户手势策略失败，静默处理
        }
      }
      return
    }

    // 首次播放：请求 TTS 合成
    setIsLoading(true)
    try {
      const result = await speechApi.tts(text)
      if (result.audio_url) {
        setAudioUrl(result.audio_url)
        // 等待 audio 元素渲染后自动播放
        setTimeout(() => {
          audioRef.current?.play().catch(() => {
            // 自动播放可能被浏览器策略阻止
            message.info('请再次点击播放按钮收听')
          })
        }, 200)
      } else {
        message.error('语音合成失败，未获取到音频')
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : '语音合成失败'
      message.error(errMsg)
    } finally {
      setIsLoading(false)
    }
  }, [audioUrl, isPlaying, text])

  // 文本为空时不渲染
  if (!text || !text.trim()) return null

  return (
    <>
      <Tooltip title={isLoading ? '正在合成语音...' : isPlaying ? '暂停播放' : '语音播放'}>
        <Button
          type="text"
          size="small"
          icon={
            isLoading ? (
              <LoadingOutlined />
            ) : isPlaying ? (
              <PauseOutlined />
            ) : (
              <SoundOutlined />
            )
          }
          onClick={handlePlay}
          style={{
            padding: '2px 6px',
            minHeight: 'auto',
            height: 'auto',
            color: isPlaying ? '#2563eb' : '#94a3b8',
            transition: 'color 0.3s ease',
          }}
        />
      </Tooltip>
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
          onError={() => {
            setIsPlaying(false)
            message.error('音频播放失败')
          }}
          preload="auto"
        />
      )}
    </>
  )
}
