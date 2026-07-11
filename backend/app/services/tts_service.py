"""TTS 语音合成服务 — 支持 Edge-TTS / CosyVoice

Edge-TTS: 免费、无需 API Key、140+ 中文音色、音质接近真人。
CosyVoice: 阿里开源、150ms 流式延迟、声音克隆、情感控制。

音频文件存储在本地 VOICE_STORAGE_DIR，并支持 Redis 缓存。
"""
import asyncio
import hashlib
import os
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.utils.logger import app_logger
from app.services.redis_service import redis_service

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

        # 检查 Redis 缓存
        cache_key = self._get_cache_key(text, voice, rate, volume)
        if redis_service.enabled:
            cached = redis_service.get(cache_key)
            if cached:
                app_logger.debug(f"TTS 缓存命中: {cache_key}")
                import json
                try:
                    return json.loads(cached)
                except (json.JSONDecodeError, TypeError):
                    pass

        # 根据引擎选择合成方式
        if settings.TTS_ENGINE == "edge-tts":
            result = await self._edge_tts(text, voice, rate, volume)
        elif settings.TTS_ENGINE == "cosyvoice":
            result = await self._cosyvoice(text, voice, rate, volume)
        else:
            result = {"audio_url": "", "duration": 0.0, "error": f"不支持的 TTS 引擎: {settings.TTS_ENGINE}"}

        # 写入 Redis 缓存
        if result.get("audio_url") and redis_service.enabled:
            import json
            redis_service.set(cache_key, json.dumps(result, ensure_ascii=False), ttl=settings.VOICE_CACHE_TTL)

        return result

    async def _edge_tts(self, text: str, voice: str, rate: str, volume: str) -> dict:
        """使用 Edge-TTS 合成语音"""
        try:
            import edge_tts

            # 生成唯一文件名
            file_hash = hashlib.md5(f"{text}|{voice}|{rate}|{volume}".encode()).hexdigest()[:16]
            filename = f"tts_{file_hash}.{settings.TTS_AUDIO_FORMAT}"
            output_path = self._storage_dir / filename

            # 如果文件已存在，直接返回
            if output_path.exists():
                audio_url = f"/voice_files/{filename}"
                return {"audio_url": audio_url, "duration": 0.0}

            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
            await communicate.save(str(output_path))

            audio_url = f"/voice_files/{filename}"
            app_logger.info(f"✓ TTS 合成完成 (Edge-TTS): {filename}, 文本长度={len(text)}")
            return {"audio_url": audio_url, "duration": 0.0}

        except ImportError:
            app_logger.error("✗ edge-tts 未安装，请运行: uv add edge-tts")
            return {"audio_url": "", "duration": 0.0, "error": "edge-tts 未安装"}
        except Exception as e:
            app_logger.error(f"✗ Edge-TTS 合成失败: {e}", exc_info=True)
            return {"audio_url": "", "duration": 0.0, "error": str(e)}

    async def _cosyvoice(self, text: str, voice: str, rate: str, volume: str) -> dict:
        """使用 CosyVoice 合成语音（预留接口）"""
        # CosyVoice 2.0 部署较复杂，此处预留接口
        # 部署后可参考 CosyVoice 官方文档实现
        app_logger.warning("CosyVoice 引擎尚未实现，请使用 edge-tts 引擎")
        return {"audio_url": "", "duration": 0.0, "error": "CosyVoice 引擎尚未实现"}

    def health_check(self) -> dict:
        """健康检查"""
        return {
            "status": "healthy" if settings.TTS_ENABLED else "disabled",
            "engine": settings.TTS_ENGINE,
            "voice": settings.TTS_DEFAULT_VOICE,
        }


# 全局实例
tts_service = TTSService()
