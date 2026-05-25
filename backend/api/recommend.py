"""HTTP boundary for global recommendation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.api.dependencies import get_recommendation_pipeline
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.recommendation_pipeline import RecommendationPipeline
from backend.core.errors import MarketMindError

router = APIRouter(prefix="/recommend", tags=["推荐"])


class TTSRequest(BaseModel):
    project_id: str | None = None
    speech: str


class CalculateRequest(BaseModel):
    item: str
    min_confidence: float = 0.1


@router.get("/user/")
async def recommend_for_user(
    user_id: str = Query(..., description="用户ID"),
    pipeline: RecommendationPipeline = Depends(get_recommendation_pipeline),
) -> dict:
    """Recommend items for a known user id."""

    try:
        result = pipeline.recommend_user(user_id=user_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    result.setdefault("warning", None)
    return result


@router.get("/item/")
async def recommend_for_item(
    item: str = Query(..., description="商品名称"),
    pipeline: RecommendationPipeline = Depends(get_recommendation_pipeline),
) -> dict:
    """Return upstream/downstream relations for an item."""

    try:
        return pipeline.recommend_item(item=item)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc


@router.post("/calculate/")
async def calculate_rules(
    body: CalculateRequest,
    pipeline: RecommendationPipeline = Depends(get_recommendation_pipeline),
) -> dict:
    """Realtime rule calculation fallback for items missing from the model."""

    try:
        result = pipeline.calculate_rules(item=body.item, min_confidence=body.min_confidence)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    if result.get("success") is False:
        return {
            "success": False,
            "message": result.get("message", "商品不存在于数据集中"),
            "rules": [],
        }
    return result


@router.post("/tts/play/")
async def play_tts(
    body: TTSRequest,
    pipeline: RecommendationPipeline = Depends(get_recommendation_pipeline),
) -> dict:
    """Synthesize a recommendation speech clip."""

    project_id = body.project_id or "anon"
    try:
        audio = await pipeline.play_tts(project_id=project_id, speech=body.speech)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "audio_url": audio["audio_url"], "speech": body.speech}
