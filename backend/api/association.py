"""HTTP boundary for association rule analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_association_analysis_pipeline
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.association_analysis_pipeline import AssociationAnalysisPipeline
from backend.core.errors import MarketMindError
from backend.models.schemas import AssociationRuleRequest, AssociationRuleResponse

router = APIRouter()


@router.post("/analyze/", response_model=AssociationRuleResponse)
async def analyze_association_rules(
    request: AssociationRuleRequest,
    pipeline: AssociationAnalysisPipeline = Depends(get_association_analysis_pipeline),
) -> AssociationRuleResponse:
    """Run Apriori-based association analysis on the default dataset."""

    try:
        return pipeline.analyze(request)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc


@router.get("/status/")
async def get_analysis_status() -> dict:
    """Static readiness probe for the association service."""

    return {
        "success": True,
        "status": "ready",
        "message": "关联规则分析服务正常运行",
    }
