"""
推荐 API - 基于预训练模型
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from uuid import uuid4
from pathlib import Path

from backend.services.recommender_service import (
    get_recommender,
    speech_conclusion_merger,
    generate_tts,
)
from backend.core.config import settings

router = APIRouter(prefix="/recommend", tags=["推荐"])


@router.get("/user")
async def recommend_for_user(user_id: str = Query(..., description="用户ID")):
    """
    正向：输入用户ID -> 推荐商品
    """
    recommender = get_recommender()
    res = recommender.recommend_user(user_id=user_id)
    result = {
        "item": user_id,
        "recommends": res.get("recommends", []),
        "target_customers": [res["cluster"]] if res.get("cluster") else [],
        "speech": speech_conclusion_merger(res),
        "model_tries": 3,
        "human_fallback": False,
    }
    return result


@router.get("/item")
async def recommend_for_item(item: str = Query(..., description="商品名称")):
    """
    逆向：输入商品 -> 推荐目标顾客群
    """
    recommender = get_recommender()
    res = recommender.recommend_item(item_name=item)
    result = {
        "item": item,
        "recommends": res.get("rules", []),
        "target_customers": res.get("targets", []),
        "speech": speech_conclusion_merger(
            {"recommends": res.get("rules", []), "target_customers": res.get("targets", [])}
        ),
        "model_tries": 3,
        "human_fallback": False,
    }
    return result


class TTSRequest(BaseModel):
    project_id: str | None = None
    speech: str


@router.post("/tts/play")
async def play_tts(body: TTSRequest):
    """读取 speech 文本生成 MP3，并返回URL"""
    try:
        project_id = body.project_id or uuid4().hex
        audio = await generate_tts(project_id, body.speech)
        return {"success": True, "audio_url": audio["audio_url"], "speech": body.speech}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 生成失败: {e}")
