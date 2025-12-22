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
    try:
        recommender = get_recommender()
        res = recommender.recommend_user(user_id=user_id)

        # 检查是否使用了降级推荐
        warning = None
        if not recommender.has_model:
            warning = "预训练模型未加载，使用热门商品推荐"

        result = {
            "item": user_id,
            "recommends": res.get("recommends", []),
            "target_customers": [res["cluster"]] if res.get("cluster") else [],
            "speech": speech_conclusion_merger(res),
            "model_tries": 3,
            "human_fallback": False,
            "warning": warning,
        }
        return result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"数据集未找到：{str(e)}。请先创建项目并上传数据集。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


@router.get("/item")
async def recommend_for_item(item: str = Query(..., description="商品名称")):
    """
    逆向：输入商品 -> 返回双向关联拓扑图数据
    """
    try:
        recommender = get_recommender()
        res = recommender.recommend_item(item_name=item)

        result = {
            "item": item,
            "upstream": res.get("upstream", []),
            "downstream": res.get("downstream", []),
            "target_customers": res.get("target_customers", []),
            "success": True
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


class TTSRequest(BaseModel):
    project_id: str | None = None
    speech: str


class CalculateRequest(BaseModel):
    item: str
    min_confidence: float = 0.1


@router.post("/calculate")
async def calculate_rules(body: CalculateRequest):
    """
    实时计算关联规则 (Fallback)
    当预训练模型中没有找到规则时，触发实时计算
    """
    try:
        recommender = get_recommender()

        # Check if item exists in dataset first
        if body.item not in recommender.subcategories:
            return {"success": False, "message": "商品不存在于数据集中", "rules": []}

        # Trigger calculation
        rules = recommender.calculate_realtime_rules(
            item_name=body.item,
            min_confidence=body.min_confidence
        )

        return {
            "success": True,
            "item": body.item,
            "rules": rules,
            "source": "realtime_calculation"
        }
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"数据集未找到：{str(e)}。请先创建项目并上传数据集。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实时计算失败: {str(e)}")


@router.post("/tts/play")
async def play_tts(body: TTSRequest):
    """读取 speech 文本生成 MP3，并返回URL"""
    try:
        project_id = body.project_id or uuid4().hex
        audio = await generate_tts(project_id, body.speech)
        return {"success": True, "audio_url": audio["audio_url"], "speech": body.speech}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 生成失败: {e}")
