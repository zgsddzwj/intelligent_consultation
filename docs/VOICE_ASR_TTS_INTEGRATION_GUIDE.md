# 语音功能（ASR + TTS）接入指南

> 本文档详细介绍了如何在 Web 项目中接入语音识别（ASR）和语音合成（TTS）功能。
> 基于 intelligent_consultation 项目的实际实现，其他 AI 或开发者可直接按照本文档的步骤接入到自己的项目中。

---

## 目录

- [1. 架构原理](#1-架构原理)
  - [1.1 整体架构图](#11-整体架构图)
  - [1.2 ASR 语音识别原理](#12-asr-语音识别原理)
  - [1.3 TTS 语音合成原理](#13-tts-语音合成原理)
  - [1.4 技术选型对比](#14-技术选型对比)
- [2. 后端实现步骤](#2-后端实现步骤)
  - [2.1 安装依赖](#21-安装依赖)
  - [2.2 配置项](#22-配置项)
  - [2.3 TTS 语音合成服务](#23-tts-语音合成服务)
  - [2.4 ASR 语音识别服务](#24-asr-语音识别服务)
  - [2.5 API 路由](#25-api-路由)
  - [2.6 主应用挂载](#26-主应用挂载)
- [3. 前端实现步骤](#3-前端实现步骤)
  - [3.1 API 封装](#31-api-封装)
  - [3.2 语音识别 Hook（useSpeechRecognition）](#32-语音识别-hookusespeechrecognition)
  - [3.3 语音输入组件（VoiceInput）](#33-语音输入组件voiceinput)
  - [3.4 语音播放组件（VoicePlayer）](#34-语音播放组件voiceplayer)
  - [3.5 集成到聊天页面](#35-集成到聊天页面)
  - [3.6 Vite 代理配置](#36-vite-代理配置)
- [4. 完整数据流](#4-完整数据流)
- [5. 常见问题与排错](#5-常见问题与排错)

---

## 1. 架构原理

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器（前端）                         │
│                                                             │
│  ┌─────────────┐         ┌─────────────────┐                │
│  │ VoiceInput   │         │  VoicePlayer     │                │
│  │ (语音输入)    │         │  (语音播放)      │                │
│  │              │         │                  │                │
│  │ Web Speech   │         │  <audio> 标签    │                │
│  │ API 实时识别  │         │  播放 MP3        │                │
│  └──────┬───────┘         └────────┬─────────┘                │
│         │                          │                          │
│         │ 识别完成自动发送           │ 点击播放按钮              │
│         │ onSend(text)             │ 请求 TTS 合成             │
└─────────┼──────────────────────────┼──────────────────────────┘
          │                          │
          │ (ASR 走浏览器原生，        │ (TTS 走后端)
          │  不需要后端)              │
          │                          ▼
          │              ┌───────────────────────┐
          │              │   后端 FastAPI         │
          │              │                       │
          │              │  POST /api/v1/speech  │
          │              │       /tts            │
          │              │                       │
          │              │  ┌─────────────────┐  │
          │              │  │ TTSService      │  │
          │              │  │ (Edge-TTS)      │  │
          │              │  │                 │  │
          │              │  │ 1. Redis 缓存   │  │
          │              │  │ 2. 文件缓存     │  │
          │              │  │ 3. Edge-TTS    │  │
          │              │  │    在线合成     │  │
          │              │  └────────┬────────┘  │
          │              │           │           │
          │              │  /voice_files/xxx.mp3 │
          │              │  (静态文件服务)        │
          │              └───────────┬───────────┘
          │                          │
          └──────────────────────────┘
                  返回 audio_url
```

### 1.2 ASR 语音识别原理

本项目采用**双方案**设计：

#### 方案 A：浏览器 Web Speech API（主方案，默认启用）

```
用户点击麦克风
    │
    ▼
浏览器调用 SpeechRecognition API
    │
    ├── continuous=true      → 持续识别，不自动停止
    ├── interimResults=true  → 返回中间结果（实时显示文字）
    └── lang='zh-CN'         → 中文识别
    │
    ▼
Google 语音服务器（Chrome/Edge 内置，免费）
    │
    ├── onresult 事件 → 实时回调识别文字
    ├── onerror 事件  → 错误处理（权限拒绝/网络错误等）
    └── onend 事件    → 识别结束
    │
    ▼
识别完成 → 自动调用 onSend(text) 发送消息
```

**为什么选 Web Speech API？**
- 零依赖：无需安装任何 Python 包，无需 GPU
- 实时性：支持 `interimResults`，用户说话过程中就能看到文字
- 免费：Chrome/Edge 使用 Google 语音服务，无调用限制
- 兼容性：Chrome、Edge、Safari 均支持（Firefox 不支持）

**限制：**
- Chrome 需要联网（依赖 Google 语音服务）
- 需要用户授权麦克风权限
- 纯前端处理，语音数据不经过自己的服务器

#### 方案 B：后端 FunASR（可选增强方案）

```
前端 MediaRecorder 录音
    │
    ▼
上传音频文件 (webm/wav)
    │
    ▼
POST /api/v1/speech/asr
    │
    ▼
后端 FunASR Paraformer 模型推理
    │
    ├── VAD 模型 (fsmn-vad)      → 语音端点检测
    ├── ASR 模型 (paraformer-zh) → 语音转文字
    └── 标点模型 (ct-punc)       → 自动加标点
    │
    ▼
返回 {"text": "识别结果", "confidence": 0.95}
```

**适用场景：** 需要数据完全自托管、离线环境、或需要医疗术语热词优化的场景。

### 1.3 TTS 语音合成原理

```
前端点击「播放语音」按钮
    │
    ▼
POST /api/v1/speech/tts  { text: "AI回复的内容" }
    │
    ▼
后端 TTSService.synthesize()
    │
    ├── 1. 检查文本（空值/超长截断 3000 字符）
    ├── 2. 检查 Redis 缓存（MD5 哈希键）
    ├── 3. 检查本地文件缓存（文件已存在直接返回）
    └── 4. 调用 Edge-TTS 在线合成
    │
    ▼
Edge-TTS（微软免费 TTS 服务）
    │
    ├── voice: zh-CN-XiaoxiaoNeural（中文女声）
    ├── rate: +0%（语速）
    └── volume: +0%（音量）
    │
    ▼
保存为 MP3 文件 → /voice_files/tts_xxxx.mp3
    │
    ▼
写入 Redis 缓存（TTL 24小时）
    │
    ▼
返回 {"audio_url": "/voice_files/tts_xxxx.mp3"}
    │
    ▼
前端 <audio> 标签播放
```

**双层缓存设计：**
1. **Redis 缓存**：相同文本+音色+语速+音量的组合，24小时内直接返回缓存的 URL
2. **文件缓存**：相同内容的 MP3 文件不重复合成，直接返回已有文件

### 1.4 技术选型对比

#### ASR 对比

| 方案 | 准确率 | 延迟 | 成本 | 依赖 | 实时中间结果 | 离线 |
|------|--------|------|------|------|-------------|------|
| **Web Speech API** | 高 | 极低（实时） | 免费 | 无 | ✅ | ❌ |
| FunASR Paraformer | 极高 | 中（需推理） | 免费 | 需安装+模型 | ❌ | ✅ |
| OpenAI Whisper | 高 | 高 | 付费 | 需安装 | ❌ | ✅ |
| 百度/阿里云 ASR | 高 | 低 | 付费 | 无 | ✅ | ❌ |

#### TTS 对比

| 方案 | 音质 | 成本 | 延迟 | 中文音色数 | 依赖 |
|------|------|------|------|-----------|------|
| **Edge-TTS** | 接近真人 | 免费 | 低 | 140+ | pip install edge-tts |
| CosyVoice | 极高 | 免费 | 极低(流式) | 可克隆 | 需部署模型服务 |
| OpenAI TTS | 高 | 付费 | 中 | 6 | API Key |
| 百度/阿里云 TTS | 高 | 付费 | 低 | 50+ | API Key |

---

## 2. 后端实现步骤

### 2.1 安装依赖

```bash
# TTS 必装依赖（轻量）
pip install edge-tts

# ASR 可选依赖（需要 cmake，较重）
# macOS: brew install cmake
# Ubuntu: apt install cmake
pip install funasr modelscope
```

如果使用 `pyproject.toml`（推荐将 ASR 设为可选依赖）：

```toml
[project]
dependencies = [
    "edge-tts>=6.1.0",    # TTS: 微软 Edge 在线语音合成
]

[project.optional-dependencies]
speech = [
    "funasr>=1.0.0",      # ASR: 阿里 FunASR Paraformer 语音识别
    "modelscope>=1.9.0",  # FunASR 模型下载
]
```

### 2.2 配置项

在配置文件中添加以下配置项（如 `config.py`）：

```python
# ===== 语音功能配置 =====

# ASR 语音识别
ASR_ENABLED: bool = True
ASR_MODEL: str = "paraformer-zh"       # FunASR 模型名
ASR_DEVICE: str = "cpu"                # "cpu" | "cuda"
ASR_VAD_MODEL: str = "fsmn-vad"        # 语音端点检测模型
ASR_PUNC_MODEL: str = "ct-punc"        # 标点恢复模型
ASR_HOTWORDS: str = ""                 # 热词，逗号分隔（如 "高血压,糖尿病,阿司匹林"）
ASR_MAX_AUDIO_DURATION: int = 60       # 最大录音时长（秒）

# TTS 语音合成
TTS_ENABLED: bool = True
TTS_ENGINE: str = "edge-tts"           # "edge-tts" | "cosyvoice"
TTS_DEFAULT_VOICE: str = "zh-CN-XiaoxiaoNeural"  # Edge-TTS 默认音色
TTS_DEFAULT_RATE: str = "+0%"          # 语速
TTS_DEFAULT_VOLUME: str = "+0%"        # 音量
TTS_AUDIO_FORMAT: str = "mp3"          # "mp3" | "wav"

# 语音文件存储
VOICE_STORAGE_DIR: str = "./data/voice_files"  # 本地语音文件存储目录
VOICE_CACHE_TTL: int = 86400                   # 语音缓存 24 小时
```

**常用 Edge-TTS 中文音色：**

| 音色名称 | 性别 | 风格 |
|---------|------|------|
| `zh-CN-XiaoxiaoNeural` | 女 | 温暖亲切（默认） |
| `zh-CN-XiaoyiNeural` | 女 | 活泼 |
| `zh-CN-YunjianNeural` | 男 | 沉稳 |
| `zh-CN-YunxiNeural` | 男 | 阳光 |
| `zh-CN-YunxiaNeural` | 男 | 少年音 |

### 2.3 TTS 语音合成服务

创建 `tts_service.py`：

```python
"""TTS 语音合成服务 — 基于 Edge-TTS

Edge-TTS: 免费、无需 API Key、140+ 中文音色、音质接近真人。
音频文件存储在本地 VOICE_STORAGE_DIR，并支持 Redis 缓存。
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.utils.logger import app_logger
from app.services.redis_service import redis_service  # 可选，无 Redis 也能工作

settings = get_settings()


class TTSService:
    """语音合成服务（单例模式）"""

    _instance: Optional["TTSService"] = None
    _storage_dir: Path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ensure_storage_dir()
        return cls._instance

    def _ensure_storage_dir(self):
        """确保语音文件存储目录存在"""
        self._storage_dir = Path(settings.VOICE_STORAGE_DIR)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, text: str, voice: str, rate: str, volume: str) -> str:
        """生成缓存键"""
        content = f"{text}|{voice}|{rate}|{volume}"
        return f"tts:{hashlib.md5(content.encode()).hexdigest()}"

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
        :param voice: 音色名称（如 zh-CN-XiaoxiaoNeural）
        :param rate: 语速 (如 "+0%", "-10%")
        :param volume: 音量 (如 "+0%", "-20%")
        :return: {"audio_url": "url", "duration": 0.0}
        """
        if not settings.TTS_ENABLED:
            return {"audio_url": "", "duration": 0.0, "error": "TTS 服务未启用"}

        voice = voice or settings.TTS_DEFAULT_VOICE
        rate = rate or settings.TTS_DEFAULT_RATE
        volume = volume or settings.TTS_DEFAULT_VOLUME

        # 文本为空直接返回
        if not text or not text.strip():
            return {"audio_url": "", "duration": 0.0, "error": "文本内容为空"}

        # 文本超长截断保护（Edge-TTS 单次合成上限约 3100 字符）
        MAX_TTS_TEXT_LENGTH = 3000
        if len(text) > MAX_TTS_TEXT_LENGTH:
            text = text[:MAX_TTS_TEXT_LENGTH]
            app_logger.warning(f"TTS 文本过长，已截断至 {MAX_TTS_TEXT_LENGTH} 字符")

        # 检查 Redis 缓存
        cache_key = self._get_cache_key(text, voice, rate, volume)
        if redis_service.enabled:
            cached = redis_service.get(cache_key)
            if cached:
                app_logger.debug(f"TTS 缓存命中: {cache_key}")
                try:
                    return json.loads(cached)
                except (json.JSONDecodeError, TypeError):
                    pass

        # 调用 Edge-TTS 合成
        if settings.TTS_ENGINE == "edge-tts":
            result = await self._edge_tts(text, voice, rate, volume)
        else:
            result = {"audio_url": "", "duration": 0.0, "error": f"不支持的 TTS 引擎: {settings.TTS_ENGINE}"}

        # 写入 Redis 缓存
        if result.get("audio_url") and redis_service.enabled:
            redis_service.set(cache_key, json.dumps(result, ensure_ascii=False), ttl=settings.VOICE_CACHE_TTL)

        return result

    async def _edge_tts(self, text: str, voice: str, rate: str, volume: str) -> dict:
        """使用 Edge-TTS 合成语音"""
        try:
            import edge_tts

            # 生成唯一文件名（基于内容哈希，相同内容不重复合成）
            file_hash = hashlib.md5(f"{text}|{voice}|{rate}|{volume}".encode()).hexdigest()[:16]
            filename = f"tts_{file_hash}.{settings.TTS_AUDIO_FORMAT}"
            output_path = self._storage_dir / filename

            # 如果文件已存在，直接返回（文件级缓存）
            if output_path.exists():
                audio_url = f"/voice_files/{filename}"
                return {"audio_url": audio_url, "duration": 0.0}

            # 调用 Edge-TTS 合成
            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
            await communicate.save(str(output_path))

            audio_url = f"/voice_files/{filename}"
            app_logger.info(f"✓ TTS 合成完成 (Edge-TTS): {filename}, 文本长度={len(text)}")
            return {"audio_url": audio_url, "duration": 0.0}

        except ImportError:
            app_logger.error("✗ edge-tts 未安装，请运行: pip install edge-tts")
            return {"audio_url": "", "duration": 0.0, "error": "edge-tts 未安装"}
        except Exception as e:
            app_logger.error(f"✗ Edge-TTS 合成失败: {e}", exc_info=True)
            return {"audio_url": "", "duration": 0.0, "error": str(e)}

    def health_check(self) -> dict:
        """健康检查"""
        file_count = 0
        total_size = 0
        if self._storage_dir and self._storage_dir.exists():
            for f in self._storage_dir.iterdir():
                if f.is_file():
                    file_count += 1
                    total_size += f.stat().st_size

        return {
            "status": "healthy" if settings.TTS_ENABLED else "disabled",
            "engine": settings.TTS_ENGINE,
            "voice": settings.TTS_DEFAULT_VOICE,
            "storage_files": file_count,
            "storage_size_mb": round(total_size / 1024 / 1024, 2),
        }


# 全局实例
tts_service = TTSService()
```

**关键设计点：**

1. **单例模式**：`__new__` 确保全局只有一个实例，避免重复创建存储目录
2. **双层缓存**：Redis 缓存（快速命中）+ 文件缓存（持久化），相同内容不重复合成
3. **内容哈希文件名**：`tts_{md5[:16]}.mp3`，相同文本+音色+语速+音量生成相同文件名，天然去重
4. **延迟导入**：`import edge_tts` 在方法内部，未安装时不会导致整个模块加载失败

### 2.4 ASR 语音识别服务

创建 `asr_service.py`：

```python
"""ASR 语音识别服务 — 基于 FunASR Paraformer

阿里达摩院开源的端到端语音识别模型，中文识别准确率优于 Whisper。
支持 VAD（语音端点检测）和标点恢复。

模型首次加载时会从 ModelScope 下载，之后缓存在本地。
"""
import asyncio
import os
import tempfile
from typing import Optional

from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class ASRService:
    """语音识别服务（单例模式，延迟加载模型）"""

    _instance: Optional["ASRService"] = None
    _model = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """延迟加载 ASR 模型（避免启动时阻塞）"""
        if self._initialized or not settings.ASR_ENABLED:
            return

        app_logger.info("正在加载 ASR 模型 (FunASR Paraformer)...")
        try:
            from funasr import AutoModel

            model_kwargs = {
                "model": settings.ASR_MODEL,
                "vad_model": settings.ASR_VAD_MODEL,
                "punc_model": settings.ASR_PUNC_MODEL,
                "device": settings.ASR_DEVICE,
                "disable_update": True,
                "disable_pbar": True,
            }

            # 在线程中加载模型，避免阻塞事件循环
            self._model = await asyncio.to_thread(AutoModel, **model_kwargs)
            self._initialized = True
            app_logger.info("✓ ASR 模型加载完成")
        except ImportError:
            app_logger.warning("⚠ funasr 未安装，ASR 服务不可用。请运行: pip install funasr")
        except Exception as e:
            app_logger.error(f"✗ ASR 模型加载失败: {e}")

    async def recognize(self, audio_file_path: str, language: str = "zh") -> dict:
        """
        语音转文字

        :param audio_file_path: 音频文件路径（wav/mp3等）
        :param language: 语言代码
        :return: {"text": "识别结果", "confidence": 0.95}
        """
        if not self._initialized or self._model is None:
            await self.initialize()

        if self._model is None:
            return {"text": "", "confidence": 0.0, "error": "ASR 模型未加载"}

        try:
            from funasr.utils.postprocess_utils import rich_transcription_postprocess

            generate_kwargs = {
                "input": audio_file_path,
                "cache": {},
                "language": language,
            }

            # 添加热词（提升专业术语识别率）
            if settings.ASR_HOTWORDS:
                hotwords = [w.strip() for w in settings.ASR_HOTWORDS.split(",") if w.strip()]
                if hotwords:
                    generate_kwargs["hotword"] = " ".join(hotwords)

            # 在线程中执行推理，避免阻塞事件循环
            result = await asyncio.to_thread(self._model.generate, **generate_kwargs)

            if result and len(result) > 0:
                text = rich_transcription_postprocess(result[0]["text"])
                app_logger.info(f"ASR 识别结果: {text[:100]}...")
                return {"text": text, "confidence": 0.95}
            else:
                return {"text": "", "confidence": 0.0, "error": "未识别到语音内容"}

        except Exception as e:
            app_logger.error(f"ASR 识别失败: {e}", exc_info=True)
            return {"text": "", "confidence": 0.0, "error": str(e)}

    def health_check(self) -> dict:
        """健康检查"""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "model": settings.ASR_MODEL,
            "device": settings.ASR_DEVICE,
        }


# 全局实例
asr_service = ASRService()
```

**关键设计点：**

1. **延迟加载**：模型在首次调用 `recognize()` 时才加载，不影响应用启动速度
2. **线程池执行**：`asyncio.to_thread()` 避免模型推理阻塞 FastAPI 事件循环
3. **热词支持**：通过 `ASR_HOTWORDS` 配置专业术语，提升特定领域识别率
4. **VAD + 标点恢复**：自动检测语音端点 + 自动加标点符号

### 2.5 API 路由

创建 `speech.py` 路由文件：

```python
"""语音 API 路由 — ASR 语音识别 + TTS 语音合成"""
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from app.services.asr_service import asr_service
from app.services.tts_service import tts_service
from app.utils.logger import app_logger
from app.config import get_settings

settings = get_settings()
router = APIRouter()


# ========== 请求/响应模型 ==========

class TTSRequest(BaseModel):
    """TTS 请求"""
    text: str = Field(..., min_length=1, max_length=5000, description="待合成文本")
    voice: Optional[str] = Field(None, description="音色名称，如 zh-CN-XiaoxiaoNeural")
    rate: Optional[str] = Field(None, description="语速，如 +0% / -10%")
    volume: Optional[str] = Field(None, description="音量，如 +0% / -20%")


class TTSResponse(BaseModel):
    """TTS 响应"""
    audio_url: str = Field(..., description="音频文件 URL")
    duration: float = Field(0.0, description="音频时长（秒）")


class ASRResponse(BaseModel):
    """ASR 响应"""
    text: str = Field(..., description="识别出的文本")
    confidence: float = Field(..., description="置信度")


# ========== 路由 ==========

@router.post("/asr", response_model=ASRResponse, summary="语音转文字")
async def speech_to_text(
    audio_file: UploadFile = File(..., description="音频文件（wav/mp3/webm等）"),
    language: str = Form("zh", description="语言代码"),
):
    """语音转文字 — 接收音频文件，返回识别文本"""
    if not settings.ASR_ENABLED:
        raise HTTPException(status_code=503, detail="ASR 服务未启用")

    # 校验文件大小
    content = await audio_file.read()
    max_size = settings.MAX_UPLOAD_SIZE
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"音频文件过大，最大 {max_size // 1024 // 1024}MB")

    # 保存到临时文件（FunASR 需要文件路径，不接受流）
    suffix = os.path.splitext(audio_file.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        app_logger.info(f"ASR 请求: filename={audio_file.filename}, size={len(content)} bytes")
        result = await asr_service.recognize(tmp_path, language)

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        return ASRResponse(
            text=result["text"],
            confidence=result["confidence"],
        )
    finally:
        os.unlink(tmp_path)  # 清理临时文件


@router.post("/tts", response_model=TTSResponse, summary="文字转语音")
async def text_to_speech(request: TTSRequest):
    """文字转语音 — 接收文本，返回音频文件 URL"""
    if not settings.TTS_ENABLED:
        raise HTTPException(status_code=503, detail="TTS 服务未启用")

    app_logger.info(f"TTS 请求: text_length={len(request.text)}, voice={request.voice}")
    result = await tts_service.synthesize(
        text=request.text,
        voice=request.voice,
        rate=request.rate,
        volume=request.volume,
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return TTSResponse(
        audio_url=result["audio_url"],
        duration=result["duration"],
    )


@router.get("/health", summary="语音服务健康检查")
async def voice_health():
    """语音服务健康检查"""
    return {
        "asr": asr_service.health_check(),
        "tts": tts_service.health_check(),
    }
```

### 2.6 主应用挂载

在 FastAPI 的 `main.py` 中添加以下内容：

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import get_settings

settings = get_settings()

# 1. 挂载语音文件静态目录（让前端能访问 /voice_files/xxx.mp3）
voice_dir = Path(settings.VOICE_STORAGE_DIR)
voice_dir.mkdir(parents=True, exist_ok=True)
app.mount("/voice_files", StaticFiles(directory=str(voice_dir)), name="voice_files")

# 2. 注册语音 API 路由
from app.api.v1 import speech
app.include_router(speech.router, prefix=f"{settings.API_V1_PREFIX}/speech", tags=["语音"])

# 3. 在安全头中允许麦克风（Permissions-Policy）
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation()"
    return response
```

---

## 3. 前端实现步骤

### 3.1 API 封装

创建 `src/services/speech.ts`：

```typescript
import { post } from './api'

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

/**
 * 语音 API 服务
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
```

### 3.2 语音识别 Hook（useSpeechRecognition）

创建 `src/hooks/useSpeechRecognition.ts`：

```typescript
import { useState, useRef, useCallback, useEffect, useMemo } from 'react'

interface UseSpeechRecognitionReturn {
  isListening: boolean
  interimTranscript: string   // 实时中间结果
  finalTranscript: string     // 最终识别结果
  error: string | null
  isSupported: boolean        // 浏览器是否支持
  startListening: () => void
  stopListening: () => void
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
    recognition.continuous = true        // 持续识别
    recognition.interimResults = true    // 返回中间结果
    recognition.maxAlternatives = 1

    // 识别结果回调
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

    // 错误处理
    recognition.onerror = (event: any) => {
      let msg = '语音识别失败'
      switch (event.error) {
        case 'no-speech':      msg = '未检测到语音，请重试'; break
        case 'audio-capture':  msg = '无法访问麦克风，请检查设备'; break
        case 'not-allowed':    msg = '麦克风权限被拒绝，请在浏览器设置中允许'; break
        case 'network':        msg = '网络错误，语音识别需要联网'; break
        case 'aborted':        return  // 用户主动取消，不提示
        default:               msg = `语音识别错误: ${event.error}`
      }
      setError(msg)
    }

    // 识别结束
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
      } catch { /* 忽略 */ }
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
        try { recognitionRef.current.abort() } catch { /* 忽略 */ }
      }
    }
  }, [])

  return {
    isListening, interimTranscript, finalTranscript, error, isSupported,
    startListening, stopListening, resetTranscript,
  }
}
```

### 3.3 语音输入组件（VoiceInput）

创建 `src/components/voice/VoiceInput.tsx`：

```typescript
import { useState, useEffect, useCallback, useRef } from 'react'
import { Button, Tooltip, message } from 'antd'
import { AudioOutlined, LoadingOutlined } from '@ant-design/icons'
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition'

interface VoiceInputProps {
  /** 语音识别结果回调 */
  onTranscript: (text: string) => void
  /** 识别完成后自动发送（可选，不传则只填充输入框） */
  onSend?: (text: string) => void
  /** 是否禁用 */
  disabled?: boolean
  /** 按钮样式：'circle' 圆形 | 'rounded' 圆角方形 */
  variant?: 'circle' | 'rounded'
}

/**
 * 语音输入组件
 *
 * 工作流程：
 * 1. 点击麦克风按钮 → 开始实时语音识别
 * 2. 识别过程中显示浮动提示条 + 实时文字
 * 3. 再次点击 → 停止识别
 * 4. 自动调用 onSend(text) 发送消息（如果提供了 onSend）
 *    否则调用 onTranscript(text) 填入输入框
 */
export default function VoiceInput({
  onTranscript, onSend, disabled = false, variant = 'rounded',
}: VoiceInputProps) {
  const isCircle = variant === 'circle'

  // ⚠️ 关键：用 ref 存储回调，避免回调引用变化触发 useEffect 无限循环
  const onTranscriptRef = useRef(onTranscript)
  const onSendRef = useRef(onSend)
  onTranscriptRef.current = onTranscript
  onSendRef.current = onSend

  const finalTextRef = useRef('')
  const [autoSendTriggered, setAutoSendTriggered] = useState(false)

  const {
    isListening, interimTranscript, finalTranscript, error, isSupported,
    startListening, stopListening, resetTranscript,
  } = useSpeechRecognition('zh-CN')

  // 错误提示
  useEffect(() => {
    if (error) message.error(error)
  }, [error])

  // 实时更新输入框（让用户看到识别进度）
  useEffect(() => {
    if (finalTranscript) {
      finalTextRef.current = finalTranscript
      onTranscriptRef.current(finalTranscript)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finalTranscript])

  // 识别停止后自动发送
  useEffect(() => {
    if (!isListening && finalTextRef.current && !autoSendTriggered) {
      const text = finalTextRef.current.trim()
      if (text) {
        setAutoSendTriggered(true)
        if (onSendRef.current) {
          onSendRef.current(text)
        } else {
          onTranscriptRef.current(text)
        }
      }
      finalTextRef.current = ''
      resetTranscript()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isListening, autoSendTriggered])

  const handleClick = useCallback(() => {
    if (!isSupported) {
      message.warning('当前浏览器不支持语音识别，请使用 Chrome、Edge 或 Safari 浏览器')
      return
    }

    if (isListening) {
      stopListening()
    } else {
      setAutoSendTriggered(false)
      finalTextRef.current = ''
      resetTranscript()
      startListening()
    }
  }, [isListening, isSupported, startListening, stopListening, resetTranscript])

  // ... 按钮样式和渲染（参见完整源码）

  return (
    <>
      <Tooltip title={isListening ? '正在聆听... 点击停止并发送' : '语音输入（点击开始说话）'}>
        <Button
          type="text"
          icon={isListening ? <LoadingOutlined /> : <AudioOutlined />}
          onClick={handleClick}
          disabled={disabled || !isSupported}
          style={{
            borderRadius: isCircle ? '50%' : '12px',
            height: isCircle ? '44px' : '56px',
            width: isCircle ? '44px' : '56px',
            background: isListening ? 'rgba(239, 68, 68, 0.12)' : 'rgba(37, 99, 235, 0.06)',
            color: isListening ? '#ef4444' : '#2563eb',
          }}
        />
      </Tooltip>

      {/* 录音中的浮动提示条 */}
      {isListening && (
        <div style={{
          position: 'fixed', bottom: '120px', left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(0, 0, 0, 0.75)', color: '#fff',
          padding: '8px 20px', borderRadius: '20px', fontSize: '14px',
          zIndex: 1000,
        }}>
          {interimTranscript || '正在聆听...'}
        </div>
      )}
    </>
  )
}
```

**⚠️ 关键注意事项：避免 React 无限循环**

父组件传入的 `onTranscript` 和 `onSend` 通常是内联箭头函数（如 `onTranscript={(text) => setInput(text)}`），每次渲染都会创建新引用。如果直接放在 `useEffect` 依赖数组中，会导致：

```
finalTranscript 变了 → effect 触发 → 调用 onTranscript → setInput → 父组件重渲染
→ onTranscript 是新引用 → effect 又触发 → 无限循环 💥
```

**解决方案：用 `useRef` 存储回调，从依赖数组中移除：**

```typescript
const onTranscriptRef = useRef(onTranscript)
onTranscriptRef.current = onTranscript  // 每次渲染更新 ref

useEffect(() => {
  if (finalTranscript) {
    onTranscriptRef.current(finalTranscript)  // 通过 ref 调用
  }
}, [finalTranscript])  // 依赖数组只有 finalTranscript
```

### 3.4 语音播放组件（VoicePlayer）

创建 `src/components/voice/VoicePlayer.tsx`：

```typescript
import { useState, useRef, useCallback, useEffect } from 'react'
import { Button, Tooltip, message } from 'antd'
import { SoundOutlined, PauseOutlined, LoadingOutlined } from '@ant-design/icons'
import { speechApi } from '../../services/speech'

interface VoicePlayerProps {
  text: string           // 待播放的文本（可为 Markdown）
  messageId?: string     // 消息 ID
}

/**
 * 将 Markdown 文本清理为适合 TTS 朗读的纯文本
 * 移除标题标记、加粗/斜体、链接、图片、代码块、表格等
 */
function cleanMarkdownForTTS(md: string): string {
  return md
    .replace(/```[\s\S]*?```/g, '（代码）')        // 代码块
    .replace(/`([^`]+)`/g, '$1')                    // 行内代码
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')       // 图片
    .replace(/\[([^\]]*)\]\([^)]+\)/g, '$1')        // 链接
    .replace(/^#{1,6}\s+/gm, '')                    // 标题
    .replace(/\*\*([^*]+)\*\*/g, '$1')              // 加粗
    .replace(/\*([^*]+)\*/g, '$1')                  // 斜体
    .replace(/~~([^~]+)~~/g, '$1')                  // 删除线
    .replace(/^\|[-:\s|]+\|$/gm, '')                // 表格分隔行
    .replace(/\|/g, '，')                            // 表格管道符
    .replace(/^>\s+/gm, '')                          // 引用
    .replace(/^[-*+]\s+/gm, '')                     // 无序列表
    .replace(/^\d+\.\s+/gm, '')                     // 有序列表
    .replace(/^---+$/gm, '')                         // 分割线
    .replace(/\n{3,}/g, '\n\n')                     // 多余空行
    .trim()
}

/**
 * 语音播放组件
 *
 * 点击播放按钮 → 后端 TTS 合成 → <audio> 播放
 * 支持播放/暂停切换，首次播放请求后端，之后用缓存的 URL
 */
export default function VoicePlayer({ text }: VoicePlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handlePlay = useCallback(async () => {
    // 已有音频 URL：播放/暂停切换
    if (audioUrl && audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause()
      } else {
        try { await audioRef.current.play() } catch { /* 静默 */ }
      }
      return
    }

    // 首次播放：请求 TTS 合成
    const ttsText = cleanMarkdownForTTS(text)
    if (!ttsText) return

    setIsLoading(true)
    try {
      const result = await speechApi.tts(ttsText)
      if (result.audio_url) {
        setAudioUrl(result.audio_url)
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

  // 卸载时停止播放
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.src = ''
      }
    }
  }, [])

  if (!text || !text.trim()) return null

  return (
    <>
      <Tooltip title={isLoading ? '正在合成语音...' : isPlaying ? '暂停播放' : '播放语音'}>
        <Button
          type="text"
          size="small"
          icon={isLoading ? <LoadingOutlined /> : isPlaying ? <PauseOutlined /> : <SoundOutlined />}
          onClick={handlePlay}
          style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            padding: '2px 8px', height: '28px', fontSize: '12px',
            color: isPlaying ? '#2563eb' : '#94a3b8',
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
          onError={() => { setIsPlaying(false); message.error('音频播放失败') }}
          preload="auto"
        />
      )}
    </>
  )
}
```

**关键设计点：**

1. **Markdown 清理**：`cleanMarkdownForTTS()` 在发送给 TTS 前移除所有 Markdown 语法，确保朗读自然语言
2. **懒加载**：只有用户点击播放才请求后端合成，不预加载
3. **播放/暂停切换**：首次请求合成，之后复用 `<audio>` 元素切换播放状态
4. **卸载清理**：组件卸载时停止播放并释放资源

### 3.5 集成到聊天页面

在聊天页面中集成 `VoiceInput` 和 `VoicePlayer`：

```tsx
import VoiceInput from '../components/voice/VoiceInput'
import VoicePlayer from '../components/voice/VoicePlayer'

// 在聊天页面组件中：

// 语音识别完成后直接发送消息
const handleVoiceSend = useCallback((text: string) => {
  if (!text.trim() || isStreaming) return
  addMessage({ role: 'user', content: text.trim() })
  handleStreamChat(text.trim())
}, [isStreaming, addMessage, handleStreamChat])

// 输入区域中添加 VoiceInput
<div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
  <VoiceInput
    onTranscript={(text) => setInput(text)}  // 实时显示识别进度
    onSend={handleVoiceSend}                  // 识别完成自动发送
    disabled={isStreaming}
    variant="circle"
  />
  {/* 其他按钮... */}
</div>

// AI 消息底部添加 VoicePlayer（流式输出完成后显示）
{!isUser && message.content && !message.isStreaming && (
  <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
    <VoicePlayer text={message.content} messageId={message.id} />
    {/* 复制按钮等... */}
  </div>
)}
```

### 3.6 Vite 代理配置

在 `vite.config.ts` 中添加 `/voice_files` 代理，让开发环境能通过 Vite 访问后端的音频文件：

```typescript
export default defineConfig(({ mode }) => ({
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/voice_files': {                    // ← 新增：代理音频文件请求
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
}))
```

---

## 4. 完整数据流

### 语音输入流程（ASR）

```
用户点击麦克风按钮
    │
    ├──► useSpeechRecognition.startListening()
    │    └──► new webkitSpeechRecognition()
    │         ├── lang = 'zh-CN'
    │         ├── continuous = true
    │         └── interimResults = true
    │
    ├──► 用户说话...
    │    └──► onresult 事件持续触发
    │         ├── interimTranscript → 浮动提示条实时显示
    │         └── finalTranscript → setInput(text) 填入输入框
    │
    ├──► 用户再次点击 → stopListening()
    │    └──► recognition.stop()
    │         └──► onend 事件 → isListening = false
    │
    └──► useEffect 检测到 isListening=false 且有文本
         └──► onSend(text) → addMessage() + handleStreamChat()
              └──► AI 回复...
```

### 语音播放流程（TTS）

```
AI 回复完成（isStreaming=false）
    │
    ├──► 显示「播放语音」按钮
    │
    ├──► 用户点击播放
    │    └──► cleanMarkdownForTTS(text)  清理 Markdown
    │    └──► speechApi.tts(ttsText)
    │         └──► POST /api/v1/speech/tts { text: "..." }
    │
    ├──► 后端 TTSService.synthesize()
    │    ├── 1. 检查 Redis 缓存 → 命中则直接返回
    │    ├── 2. 检查文件缓存 → 文件存在则直接返回
    │    └── 3. 调用 Edge-TTS 合成 → 保存 MP3 → 写入缓存
    │
    ├──► 返回 { audio_url: "/voice_files/tts_xxxx.mp3" }
    │
    ├──► setAudioUrl(audioUrl)
    │    └──► <audio src="/voice_files/tts_xxxx.mp3" /> 渲染
    │
    └──► 自动播放 → 用户听到语音
         └──► 再次点击 → 暂停/播放切换
```

---

## 5. 常见问题与排错

### Q1: 录音后没有发送消息？

**检查清单：**
1. 确认传入了 `onSend` 回调给 `VoiceInput` 组件
2. 确认 `onSend` 内部没有 `if (!input.trim()) return` 的判断（语音发送不需要检查 input 变量）
3. 确认浏览器支持 Web Speech API（`isSupported` 为 true）
4. 打开浏览器控制台查看是否有权限错误

### Q2: 浏览器不支持语音识别？

Web Speech API 兼容性：

| 浏览器 | 支持情况 |
|--------|---------|
| Chrome | ✅ 完全支持（需联网） |
| Edge | ✅ 完全支持（需联网） |
| Safari | ✅ 支持（iOS 14.5+） |
| Firefox | ❌ 不支持 |

如果不支持，组件会自动禁用麦克风按钮并提示用户。

### Q3: TTS 语音播放失败？

**检查清单：**
1. 确认后端已安装 `edge-tts`：`pip install edge-tts`
2. 确认 `TTS_ENABLED=True`（配置文件）
3. 测试后端接口：`curl -X POST http://localhost:8000/api/v1/speech/tts -H "Content-Type: application/json" -d '{"text":"测试"}'`
4. 确认 `/voice_files` 静态目录已挂载
5. 确认 Vite 代理配置了 `/voice_files`

### Q4: React 出现 "Maximum update depth exceeded"？

**原因：** `onTranscript` / `onSend` 是内联箭头函数，每次渲染创建新引用，导致 `useEffect` 无限触发。

**解决：** 用 `useRef` 存储回调，从 `useEffect` 依赖数组中移除。详见 [3.3 节](#33-语音输入组件voiceinput)的说明。

### Q5: Edge-TTS 合成报错？

- **网络问题：** Edge-TTS 需要访问微软服务器，确保网络通畅
- **文本过长：** Edge-TTS 单次合成上限约 3100 字符，代码中已做 3000 字符截断保护
- **音色名称错误：** 使用完整的音色名称（如 `zh-CN-XiaoxiaoNeural`），不要简写

### Q6: 如何切换 ASR 方案（浏览器 vs 后端 FunASR）？

**默认方案（浏览器 Web Speech API）：** 无需任何后端配置，前端开箱即用。

**切换到后端 FunASR：**
1. 安装依赖：`brew install cmake && pip install funasr modelscope`
2. 配置 `ASR_ENABLED=True`
3. 前端改用 `MediaRecorder` 录音 + `speechApi.asr()` 上传识别（需要修改 `VoiceInput` 组件）

### Q7: 如何自定义音色？

修改后端配置或前端请求时传入 `voice` 参数：

```typescript
// 前端指定音色
const result = await speechApi.tts(text, 'zh-CN-YunjianNeural')  // 男声
```

或在后端配置文件中修改默认音色：

```python
TTS_DEFAULT_VOICE: str = "zh-CN-YunjianNeural"  # 改为男声
```
