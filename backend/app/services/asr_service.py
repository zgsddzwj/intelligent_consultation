"""ASR 语音识别服务 — 基于 FunASR Paraformer

阿里达摩院开源的端到端语音识别模型，中文识别准确率优于 Whisper。
支持 VAD（语音端点检测）和标点恢复，适合医疗咨询场景。

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
            app_logger.warning("⚠ funasr 未安装，ASR 服务不可用。请运行: uv add funasr")
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

            # 构建生成参数
            generate_kwargs = {
                "input": audio_file_path,
                "cache": {},
                "language": language,
            }

            # 添加热词（医疗术语）
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
