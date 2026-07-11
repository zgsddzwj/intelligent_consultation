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


class VoiceHealthResponse(BaseModel):
    """语音服务健康检查响应"""
    asr: dict = Field(..., description="ASR 服务状态")
    tts: dict = Field(..., description="TTS 服务状态")


# ========== 路由 ==========

@router.post("/asr", response_model=ASRResponse, summary="语音转文字", description="上传音频文件，返回识别文本")
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

    # 保存到临时文件
    suffix = os.path.splitext(audio_file.filename or "audio.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        app_logger.info(f"ASR 请求: filename={audio_file.filename}, size={len(content)} bytes")
        result = await asr_service.recognize(tmp_path, language)

        if result.get("error"):
            app_logger.warning(f"ASR 识别异常: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])

        return ASRResponse(
            text=result["text"],
            confidence=result["confidence"],
        )
    finally:
        os.unlink(tmp_path)


@router.post("/tts", response_model=TTSResponse, summary="文字转语音", description="输入文本，返回语音播放 URL")
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
        app_logger.warning(f"TTS 合成异常: {result['error']}")
        raise HTTPException(status_code=500, detail=result["error"])

    return TTSResponse(
        audio_url=result["audio_url"],
        duration=result["duration"],
    )


@router.get("/health", response_model=VoiceHealthResponse, summary="语音服务健康检查")
async def voice_health():
    """语音服务健康检查"""
    return VoiceHealthResponse(
        asr=asr_service.health_check(),
        tts=tts_service.health_check(),
    )
