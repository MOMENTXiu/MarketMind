"""
用户购买行为推荐 API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from uuid import uuid4
from pathlib import Path

from backend.core.analysis import recommend_from_behavior
from backend.core.config import settings
from backend.services.tts_service import TTSService

router = APIRouter(prefix="/recommend", tags=["行为推荐"])


@router.get("/user")
async def recommend_for_user(user_id: str = Query(..., description="用户ID"), dataset: str | None = None):
    data_path = dataset or settings.DATA_PATH
    return recommend_from_behavior(data_path, user_id)


@router.get("/product")
async def recommend_for_product(item: str = Query(..., description="商品名称"), dataset: str | None = None):
    data_path = dataset or settings.DATA_PATH
    return recommend_from_behavior(data_path, item)


class TTSRequest(BaseModel):
    speech: str


@router.post("/tts/play")
async def play_tts(body: TTSRequest):
    """读取 speech 文本生成 MP3，并返回URL"""
    try:
        audio_dir = Path(settings.AUDIO_DIR if hasattr(settings, "AUDIO_DIR") else "outputs/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"recommend_{uuid4().hex}.mp3"
        audio_path = audio_dir / file_name
        tts = TTSService()
        await tts.synthesize(body.speech, str(audio_path))
        return {
            "success": True,
            "audio_url": f"/outputs/audio/{file_name}",
            "path": str(audio_path),
            "speech": body.speech,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 生成失败: {e}")
