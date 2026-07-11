# 🎯 TTS+ASR 语音功能开发计划（v2 — 后端模型驱动架构）

## 📋 项目概述

为智能医疗咨询平台添加完整的语音功能：
- **ASR (Automatic Speech Recognition)**：用户语音输入实时转为文字
- **TTS (Text-to-Speech)**：AI 回复文字转为语音播放
- 实现类似"豆包"App 的语音交互体验

---

## ❗ 核心架构决策：为什么不能纯前端实现

### 纯前端 Web Speech API 的致命问题

| 问题 | 详细说明 |
|------|----------|
| **🔴 隐私合规风险** | Chrome 的 `SpeechRecognition` 实际将音频发送到 Google 服务器处理，并非真正的端侧识别。医疗平台的患者语音数据涉及隐私，不能发送到第三方 |
| **🔴 TTS 音质差** | 浏览器 `SpeechSynthesis` 使用操作系统自带的 TTS 引擎，声音机械、不自然，完全达不到"豆包"级别体验 |
| **🔴 浏览器兼容性差** | Firefox 完全不支持 `SpeechRecognition`；Safari 支持有限；不同浏览器行为不一致 |
| **🔴 无法定制** | 无法针对医疗术语优化识别、无法控制语音情感/韵律、无法做声音克隆 |
| **🔴 当前安全策略冲突** | 项目 `main.py` 第 396 行已设置 `Permissions-Policy: microphone=()` — 麦克风权限被完全禁用 |

### 正确架构：后端语音模型 + 前端录音/播放

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React)                          │
│  MediaRecorder API 录音 → 上传音频文件 → 接收文本/音频URL    │
│  <audio> 标签播放 TTS 音频                                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                    后端 (FastAPI)                            │
│                                                              │
│  ┌─────────────┐         ┌──────────────────┐              │
│  │  ASR 服务   │         │  TTS 服务        │              │
│  │  FunASR     │         │  Edge-TTS (快速) │              │
│  │  Paraformer │         │  CosyVoice (高质)│              │
│  └─────────────┘         └──────────────────┘              │
│                                                              │
│  ┌──────────────────────────────────────────┐               │
│  │  MinIO (音频文件存储)                    │               │
│  │  Redis (识别结果缓存)                    │               │
│  └──────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术选型

### ASR 语音识别 — 后端模型

| 方案 | 模型/服务 | 优势 | 劣势 | 适用场景 |
|------|-----------|------|------|----------|
| **✅ 推荐** | **FunASR (Paraformer)** | 阿里开源，中文识别准确率超 Whisper，支持流式，60000小时工业数据训练，支持热词定制 | 需要 GPU 推理（CPU 也可但较慢） | 生产环境首选 |
| 备选 | **OpenAI Whisper** | 多语言支持（99种语言），社区活跃 | 中文准确率略低于 Paraformer，模型较大 | 多语言场景 |
| 备选 | **阿里云 ASR API** | 免部署，高准确率 | 按调用量收费，数据需上传云 | 快速验证 |

### TTS 语音合成 — 后端模型

| 方案 | 模型/服务 | 优势 | 劣势 | 适用场景 |
|------|-----------|------|------|----------|
| **✅ 快速启动** | **Edge-TTS** | 免费、无需 API Key、140+音色、中文方言支持（粤语/东北话/陕西话等）、音质接近真人 | 依赖微软在线服务 | 开发阶段/快速上线 |
| **✅ 最佳质量** | **CosyVoice 2.0** | 阿里开源、150ms 流式延迟、声音克隆（3-10s样本）、情感控制、MOS 5.53（超越商业模型） | 需 GPU 部署，模型约 300M | 生产环境/豆包级体验 |
| 备选 | **ChatTTS** | 专为对话场景优化，支持中英双语，韵律自然 | 仅非商用许可，音色有限 | 内部研究 |

### 技术选型建议

```
开发阶段：Edge-TTS（零成本快速验证）
         + FunASR Paraformer（CPU 模式即可）

生产阶段：CosyVoice 2.0（GPU 服务器部署）
         + FunASR Paraformer（GPU 加速）
```

---

## 📅 开发阶段规划（4周）

### **第一阶段：后端语音服务搭建（第1周）**

#### 1.1 依赖安装与环境配置

```bash
# backend 目录下执行
# ASR: FunASR
uv add funasr modelscope torch torchaudio

# TTS: Edge-TTS（开发阶段，零成本）
uv add edge-tts

# TTS: CosyVoice 2.0（生产阶段，可选）
# 需单独安装，参见 https://github.com/FunAudioLLM/CosyVoice

# 音频处理工具
uv add pydub soundfile
```

#### 1.2 配置项扩展

在 `backend/app/config.py` 的 `Settings` 类中新增：

```python
# ===== 语音功能配置 =====
# ASR 配置
ASR_ENABLED: bool = True
ASR_MODEL: str = "paraformer-zh"  # FunASR 模型名
ASR_DEVICE: str = "cpu"  # "cpu" | "cuda"
ASR_VAD_MODEL: str = "fsmn-vad"
ASR_PUNC_MODEL: str = "ct-punc"
ASR_HOTWORDS: str = ""  # 医疗热词，逗号分隔
ASR_MAX_AUDIO_DURATION: int = 60  # 最大录音时长（秒）

# TTS 配置
TTS_ENABLED: bool = True
TTS_ENGINE: str = "edge-tts"  # "edge-tts" | "cosyvoice"
TTS_DEFAULT_VOICE: str = "zh-CN-XiaoxiaoNeural"  # Edge-TTS 默认音色
TTS_DEFAULT_RATE: str = "+0%"  # 语速
TTS_DEFAULT_VOLUME: str = "+0%"  # 音量
TTS_AUDIO_FORMAT: str = "mp3"  # "mp3" | "wav"

# 语音文件存储
VOICE_STORAGE_BUCKET: str = "voice-files"
VOICE_CACHE_TTL: int = 86400  # 语音缓存 24 小时
```

#### 1.3 ASR 服务实现

创建 `backend/app/services/asr_service.py`:

```python
"""ASR 语音识别服务 — 基于 FunASR Paraformer"""
import asyncio
import tempfile
from typing import Optional
from loguru import logger

class ASRService:
    """语音识别服务（单例）"""
    
    _instance: Optional["ASRService"] = None
    _model = None
    _vad_model = None
    _punc_model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """延迟加载模型（避免启动时阻塞）"""
        from app.config import get_settings
        settings = get_settings()
        
        if not settings.ASR_ENABLED:
            return
        
        logger.info("正在加载 ASR 模型...")
        from funasr import AutoModel
        
        self._model = AutoModel(
            model=settings.ASR_MODEL,
            vad_model=settings.ASR_VAD_MODEL,
            punc_model=settings.ASR_PUNC_MODEL,
            device=settings.ASR_DEVICE,
            disable_update=True,
        )
        logger.info("✓ ASR 模型加载完成")
    
    async def recognize(self, audio_file_path: str, language: str = "zh") -> dict:
        """
        语音转文字
        :param audio_file_path: 音频文件路径
        :param language: 语言
        :return: {"text": "识别结果", "confidence": 0.95}
        """
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
        
        result = await asyncio.to_thread(
            self._model.generate,
            input=audio_file_path,
            cache={},
            language=language,
        )
        
        text = rich_transcription_postprocess(result[0]["text"])
        return {"text": text, "confidence": 0.95}
```

#### 1.4 TTS 服务实现

创建 `backend/app/services/tts_service.py`:

```python
"""TTS 语音合成服务 — 支持 Edge-TTS / CosyVoice"""
import asyncio
import os
from typing import Optional
from loguru import logger

class TTSService:
    """语音合成服务（单例）"""
    
    _instance: Optional["TTSService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        volume: Optional[str] = None,
    ) -> dict:
        """
        文字转语音
        :param text: 待合成文本
        :param voice: 音色名称
        :param rate: 语速 (如 "+0%", "-10%")
        :param volume: 音量 (如 "+0%", "-20%")
        :return: {"audio_url": "url", "duration": 3.5}
        """
        from app.config import get_settings
        settings = get_settings()
        
        voice = voice or settings.TTS_DEFAULT_VOICE
        rate = rate or settings.TTS_DEFAULT_RATE
        volume = volume or settings.TTS_DEFAULT_VOLUME
        
        if settings.TTS_ENGINE == "edge-tts":
            return await self._edge_tts(text, voice, rate, volume)
        elif settings.TTS_ENGINE == "cosyvoice":
            return await self._cosyvoice(text, voice, rate, volume)
    
    async def _edge_tts(self, text, voice, rate, volume) -> dict:
        """Edge-TTS 合成"""
        import edge_tts
        
        # 生成唯一文件名
        import hashlib
        file_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        output_path = f"/tmp/tts_{file_hash}.mp3"
        
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
        await communicate.save(output_path)
        
        # 上传到 MinIO 并获取 URL
        from app.services.object_storage import get_object_storage
        storage = get_object_storage()
        audio_url = await storage.upload_file(
            output_path,
            bucket_name="voice-files",
            object_name=f"tts/{file_hash}.mp3",
        )
        
        # 清理临时文件
        os.remove(output_path)
        
        return {"audio_url": audio_url, "duration": 0.0}  # duration 可后续计算
```

#### 1.5 API 路由

创建 `backend/app/api/v1/speech.py`:

```python
"""语音 API 路由"""
from fastapi import APIRouter, UploadFile, File, Form
from app.services.asr_service import ASRService
from app.services.tts_service import TTSService
from app.utils.logger import app_logger

router = APIRouter()

@router.post("/asr")
async def speech_to_text(
    audio_file: UploadFile = File(...),
    language: str = Form("zh"),
):
    """语音转文字 — 接收音频文件，返回识别文本"""
    asr = ASRService()
    
    # 保存上传的音频到临时文件
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await audio_file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = await asr.recognize(tmp_path, language)
        return {"text": result["text"], "confidence": result["confidence"]}
    finally:
        import os
        os.unlink(tmp_path)

@router.post("/tts")
async def text_to_speech(
    text: str = Form(...),
    voice: str = Form(""),
    rate: str = Form(""),
    volume: str = Form(""),
):
    """文字转语音 — 接收文本，返回音频文件 URL"""
    tts = TTSService()
    result = await tts.synthesize(text, voice or None, rate or None, volume or None)
    return result
```

在 `backend/app/main.py` 中注册路由：

```python
from app.api.v1 import consultation, agents, knowledge, users, image_analysis, health, speech
app.include_router(speech.router, prefix=f"{settings.API_V1_PREFIX}/speech", tags=["语音"])
```

**⚠️ 关键：修改安全策略头部**

`main.py` 第 396 行，将 `microphone=()` 改为允许麦克风：

```python
# 修改前：
response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
# 修改后：
response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
```

---

### **第二阶段：前端录音与播放（第2周）**

#### 2.1 前端依赖

```bash
cd frontend
npm install lucide-react  # 图标库（如未安装）
```

#### 2.2 语音 API 服务

创建 `frontend/src/services/speech.ts`:

```typescript
import apiClient from './api'

/** ASR 语音识别响应 */
export interface ASRResponse {
  text: string
  confidence: number
}

/** TTS 语音合成响应 */
export interface TTSResponse {
  audio_url: string
  duration: number
}

export const speechApi = {
  /** 语音转文字 */
  asr: async (audioBlob: Blob): Promise<ASRResponse> => {
    const formData = new FormData()
    formData.append('audio_file', audioBlob, 'recording.wav')
    formData.append('language', 'zh')
    
    const response = await apiClient.post('/speech/asr', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000, // ASR 需要更长的超时
    })
    return response
  },

  /** 文字转语音 */
  tts: async (text: string, voice?: string): Promise<TTSResponse> => {
    const formData = new FormData()
    formData.append('text', text)
    if (voice) formData.append('voice', voice)
    
    const response = await apiClient.post('/speech/tts', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    })
    return response
  },
}
```

#### 2.3 录音 Hook

创建 `frontend/src/hooks/useAudioRecorder.ts`:

```typescript
import { useState, useRef, useCallback, useEffect } from 'react'

interface UseAudioRecorderReturn {
  isRecording: boolean
  audioBlob: Blob | null
  startRecording: () => Promise<void>
  stopRecording: () => void
  recordingTime: number
  error: string | null
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [recordingTime, setRecordingTime] = useState(0)
  const [error, setError] = useState<string | null>(null)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<number | null>(null)
  
  const startRecording = useCallback(async () => {
    try {
      setError(null)
      setAudioBlob(null)
      setRecordingTime(0)
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })
        setAudioBlob(blob)
        streamRef.current?.getTracks().forEach(t => t.stop())
      }
      
      mediaRecorder.start()
      setIsRecording(true)
      
      timerRef.current = window.setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)
    } catch (err) {
      setError('无法访问麦克风，请检查浏览器权限设置')
    }
  }, [])
  
  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop()
    setIsRecording(false)
    if (timerRef.current) clearInterval(timerRef.current)
  }, [])
  
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      streamRef.current?.getTracks().forEach(t => t.stop())
    }
  }, [])
  
  return { isRecording, audioBlob, startRecording, stopRecording, recordingTime, error }
}
```

#### 2.4 语音输入组件

创建 `frontend/src/components/voice/VoiceInput.tsx`:

```tsx
import { useState } from 'react'
import { Button, Tooltip, message } from 'antd'
import { MicOutlined, AudioMutedOutlined } from '@ant-design/icons'
import { useAudioRecorder } from '../../hooks/useAudioRecorder'
import { speechApi } from '../../services/speech'

interface VoiceInputProps {
  onTranscript: (text: string) => void
  disabled?: boolean
}

export default function VoiceInput({ onTranscript, disabled }: VoiceInputProps) {
  const [loading, setLoading] = useState(false)
  const { isRecording, audioBlob, startRecording, stopRecording, recordingTime, error } = useAudioRecorder()
  
  const handleClick = async () => {
    if (isRecording) {
      stopRecording()
      // 等待 audioBlob 生成后发送识别
      if (audioBlob) {
        setLoading(true)
        try {
          const result = await speechApi.asr(audioBlob)
          onTranscript(result.text)
        } catch {
          message.error('语音识别失败，请重试')
        } finally {
          setLoading(false)
        }
      }
    } else {
      await startRecording()
    }
  }
  
  if (error) {
    message.error(error)
  }
  
  return (
    <Tooltip title={isRecording ? `录音中... ${recordingTime}s` : '语音输入'}>
      <Button
        type="text"
        icon={isRecording ? <AudioMutedOutlined /> : <MicOutlined />}
        onClick={handleClick}
        disabled={disabled || loading}
        loading={loading}
        style={{
          borderRadius: '12px',
          height: '56px',
          width: '56px',
          background: isRecording 
            ? 'rgba(239, 68, 68, 0.15)' 
            : 'rgba(102, 126, 234, 0.1)',
          border: `2px solid ${
            isRecording ? 'rgba(239, 68, 68, 0.3)' : 'rgba(102, 126, 234, 0.2)'
          }`,
          color: isRecording ? '#ef4444' : '#667eea',
          animation: isRecording ? 'pulse 1.5s infinite' : 'none',
        }}
      />
    </Tooltip>
  )
}
```

#### 2.5 语音播放组件

创建 `frontend/src/components/voice/VoicePlayer.tsx`:

```tsx
import { useState, useRef, useCallback, useEffect } from 'react'
import { Button, Tooltip } from 'antd'
import { SoundOutlined, PauseOutlined, LoadingOutlined } from '@ant-design/icons'
import { speechApi } from '../../services/speech'

interface VoicePlayerProps {
  text: string
  messageId: string
}

export default function VoicePlayer({ text, messageId }: VoicePlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  
  const handlePlay = async () => {
    // 如果已有音频URL，直接播放/暂停
    if (audioUrl) {
      if (isPlaying) {
        audioRef.current?.pause()
      } else {
        audioRef.current?.play()
      }
      return
    }
    
    // 首次播放：请求 TTS 合成
    setIsLoading(true)
    try {
      const result = await speechApi.tts(text)
      setAudioUrl(result.audio_url)
      // 自动播放
      setTimeout(() => audioRef.current?.play(), 100)
    } catch {
      // 错误处理
    } finally {
      setIsLoading(false)
    }
  }
  
  return (
    <>
      <Tooltip title={isPlaying ? '暂停' : '语音播放'}>
        <Button
          type="text"
          size="small"
          icon={
            isLoading ? <LoadingOutlined /> :
            isPlaying ? <PauseOutlined /> : <SoundOutlined />
          }
          onClick={handlePlay}
          style={{
            padding: '2px 6px',
            color: isPlaying ? '#2563eb' : '#94a3b8',
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
        />
      )}
    </>
  )
}
```

#### 2.6 集成到现有组件

**修改 `ChatInput.tsx`** — 添加语音输入按钮：

在图片上传按钮旁边添加 VoiceInput 组件，识别结果自动填入输入框。

**修改 `ChatMessage.tsx`** — 添加语音播放按钮：

在 AI 消息气泡的复制按钮旁边添加 VoicePlayer 组件。

---

### **第三阶段：优化与增强（第3周）**

#### 3.1 ASR 优化
- 医疗热词配置（药品名、疾病名、检查项目等）
- 音频预处理：降噪、归一化
- 识别结果缓存（Redis，相同音频不重复识别）
- 流式识别支持（WebSocket 实时传输）

#### 3.2 TTS 优化
- 语音缓存（相同文本不重复合成，MinIO + Redis）
- 长文本分段合成与拼接
- 流式播放（边合成边播放）
- 多音色选择面板

#### 3.3 前端体验优化
- 录音波形动画
- 语音播放进度条
- 录音时长限制（60秒）
- 兼容性检测与降级提示

#### 3.4 安全优化
- 麦克风权限引导
- 音频文件大小限制
- 音频文件格式校验
- 语音 API 限流

---

### **第四阶段：测试与部署（第4周）**

#### 4.1 测试
- ASR 中文准确率测试（医疗场景）
- TTS 音质评估（MOS 评分）
- 并发性能测试
- 浏览器兼容性测试
- 移动端适配测试

#### 4.2 部署
- FunASR 模型 Docker 化
- Edge-TTS / CosyVoice 部署配置
- K8s GPU 节点配置（如使用 CosyVoice）
- 监控指标接入 Prometheus

---

## 📁 文件结构

```
backend/app/
├── config.py                          # 新增语音配置项
├── main.py                            # 注册路由 + 修改麦克风权限
├── services/
│   ├── asr_service.py                 # ASR 服务 (FunASR)
│   └── tts_service.py                 # TTS 服务 (Edge-TTS/CosyVoice)
├── api/v1/
│   └── speech.py                      # 语音 API 路由
└── utils/
    └── audio_processing.py            # 音频格式转换工具

frontend/src/
├── components/voice/
│   ├── VoiceInput.tsx                 # 语音输入按钮
│   └── VoicePlayer.tsx                # 语音播放按钮
├── hooks/
│   └── useAudioRecorder.ts            # 录音 Hook
└── services/
    └── speech.ts                      # 语音 API 封装
```

---

## 📊 技术对比总结

| 维度 | 纯前端 Web Speech API | 后端模型方案（推荐） |
|------|----------------------|-------------------|
| **ASR 中文准确率** | ~70-80%（医疗术语更差） | ~95%（FunASR + 热词） |
| **TTS 音质** | 机械、不自然 | 接近真人（Edge-TTS/CosyVoice） |
| **隐私合规** | ❌ 音频发送到 Google | ✅ 数据在自有服务器处理 |
| **浏览器兼容** | Chrome/Edge only | 全浏览器支持 |
| **可控性** | 不可定制 | 热词、音色、情感、语速全可控 |
| **部署成本** | 零 | 需 CPU/GPU 资源 |
| **延迟** | 低（但依赖网络） | ASR ~200ms, TTS ~150ms |

## 🎯 成功指标

- [ ] ASR 中文医疗场景识别准确率 ≥ 95%
- [ ] TTS 语音合成 MOS 评分 ≥ 4.0
- [ ] ASR 响应延迟 < 500ms
- [ ] TTS 首包延迟 < 300ms（Edge-TTS）/ < 150ms（CosyVoice 流式）
- [ ] 全浏览器兼容（Chrome/Edge/Safari/Firefox）
- [ ] 语音功能崩溃率 < 0.1%
