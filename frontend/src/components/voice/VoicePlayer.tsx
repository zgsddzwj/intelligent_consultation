import { useState, useRef, useCallback, useEffect } from 'react'
import { Button, Tooltip, message } from 'antd'
import { SoundOutlined, PauseOutlined, LoadingOutlined } from '@ant-design/icons'
import { speechApi } from '../../services/speech'

interface VoicePlayerProps {
  /** 待播放的文本内容（可为 Markdown，会自动清理） */
  text: string
}

/**
 * 将 Markdown 文本清理为适合 TTS 朗读的纯文本
 * - 移除标题标记、加粗/斜体、链接、图片、代码块、表格分隔符等
 * - 保留有意义的标点和内容
 */
function cleanMarkdownForTTS(md: string): string {
  return md
    // 代码块 → 移除（含语言标识）
    .replace(/```[\s\S]*?```/g, '（代码）')
    // 行内代码
    .replace(/`([^`]+)`/g, '$1')
    // 图片 ![alt](url)
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    // 链接 [text](url) → text
    .replace(/\[([^\]]*)\]\([^)]+\)/g, '$1')
    // 标题标记 # ## ###
    .replace(/^#{1,6}\s+/gm, '')
    // 加粗/斜体 **text** / *text* / __text__ / _text_
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    // 删除线 ~~text~~
    .replace(/~~([^~]+)~~/g, '$1')
    // 表格分隔行 |---|---|
    .replace(/^\|[-:\s|]+\|$/gm, '')
    // 表格中的管道符 → 逗号
    .replace(/\|/g, '，')
    // 引用标记 >
    .replace(/^>\s+/gm, '')
    // 无序列表标记 - * +
    .replace(/^[-*+]\s+/gm, '')
    // 有序列表标记 1. 2.
    .replace(/^\d+\.\s+/gm, '')
    // 水平分割线
    .replace(/^---+$/gm, '')
    // 多余的空行
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * 语音播放组件
 *
 * 点击播放按钮，将文本发送到后端 TTS 服务（Edge-TTS）合成语音并播放。
 * 支持播放/暂停切换，首次播放会请求后端合成，之后使用缓存的音频 URL。
 * 自动清理 Markdown 标记，确保朗读的是自然语言。
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

    // 首次播放：请求 TTS 合成（清理 Markdown 标记）
    const ttsText = cleanMarkdownForTTS(text)
    if (!ttsText) return

    setIsLoading(true)
    try {
      const result = await speechApi.tts(ttsText)
      if (result.audio_url) {
        setAudioUrl(result.audio_url)
        // 等待 audio 元素渲染后自动播放
        setTimeout(() => {
          audioRef.current?.play().catch(() => {
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

  // 组件卸载时停止播放，避免音频继续播放
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.src = ''
      }
    }
  }, [])

  // 文本为空时不渲染
  if (!text || !text.trim()) return null

  return (
    <>
      <Tooltip title={isLoading ? '正在合成语音...' : isPlaying ? '暂停播放' : '播放语音'}>
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
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 8px',
            height: '28px',
            fontSize: '12px',
            color: isPlaying ? '#2563eb' : '#94a3b8',
            transition: 'color 0.3s ease',
          }}
        >
          <span>{isLoading ? '合成中' : isPlaying ? '暂停' : '播放语音'}</span>
        </Button>
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
