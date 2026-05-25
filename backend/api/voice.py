"""HTTP boundary for generic voice/TTS endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.dependencies import get_voice_synthesis_pipeline
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.voice_synthesis_pipeline import VoiceSynthesisPipeline
from backend.core.errors import MarketMindError
from backend.models.schemas import VoiceRequest, VoiceResponse

router = APIRouter()


class SimpleTTSRequest(BaseModel):
    text: str
    voice: str | None = "zh-CN-XiaoxiaoNeural"
    rate: str | None = "+0%"
    volume: str | None = "+0%"


@router.post("/tts/")
async def text_to_speech(
    request: SimpleTTSRequest,
    pipeline: VoiceSynthesisPipeline = Depends(get_voice_synthesis_pipeline),
) -> dict:
    """Synthesize text and publish through the public outputs directory."""

    try:
        return await pipeline.synthesize(
            text=request.text,
            voice=request.voice,
            rate=request.rate,
            volume=request.volume,
        )
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc


@router.post("/generate/", response_model=VoiceResponse)
async def generate_voice(request: VoiceRequest) -> VoiceResponse:
    """Placeholder broadcast generator preserved for frontend compatibility."""

    text = request.text or "MarketMind AI营销系统分析报告。功能开发中，敬请期待。"
    return VoiceResponse(
        success=True,
        message="语音生成功能开发中",
        text=text,
        audio_url="/outputs/audio/temp.mp3",
        duration=0.0,
    )


@router.get("/status/")
async def get_voice_status() -> dict:
    """Static readiness probe for the voice service."""

    return {
        "success": True,
        "status": "ready",
        "message": "语音播报服务正常运行",
    }
