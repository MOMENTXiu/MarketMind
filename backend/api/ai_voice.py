"""HTTP boundary for AI-driven voice broadcast and TTS."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.api.dependencies import get_ai_voice_broadcast_pipeline
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.ai_voice_broadcast_pipeline import AIVoiceBroadcastPipeline
from backend.core.errors import MarketMindError

router = APIRouter()


class VoiceBroadcastRequest(BaseModel):
    data: dict[str, Any]
    llm_config: dict[str, str]
    scene_type: str = "summary"
    tts_config: Optional[dict[str, str]] = None


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: Optional[str] = None
    volume: Optional[str] = None


@router.post("/ai-voice/broadcast/")
async def generate_voice_broadcast(
    request: VoiceBroadcastRequest,
    pipeline: AIVoiceBroadcastPipeline = Depends(get_ai_voice_broadcast_pipeline),
) -> dict:
    """Run LLM-driven broadcast composition followed by TTS publication."""

    try:
        return await pipeline.broadcast(
            data=request.data,
            llm_config=request.llm_config,
            scene_type=request.scene_type,
            tts_config=request.tts_config,
        )
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc


@router.post("/tts/")
async def text_to_speech(
    request: TTSRequest,
    pipeline: AIVoiceBroadcastPipeline = Depends(get_ai_voice_broadcast_pipeline),
) -> dict:
    """AI voice TTS variant served from the AI audio URL space."""

    try:
        return await pipeline.synthesize_tts(
            text=request.text,
            voice=request.voice,
            rate=request.rate,
            volume=request.volume,
        )
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc


@router.get("/ai-voice/audio/{filename}/")
async def get_audio_file(
    filename: str,
    pipeline: AIVoiceBroadcastPipeline = Depends(get_ai_voice_broadcast_pipeline),
) -> FileResponse:
    """Stream an AI voice audio asset by filename."""

    try:
        path = pipeline.resolve_audio_path(filename)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return FileResponse(
        path,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )
