"""
关联规则分析 API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.schemas import AssociationRuleRequest, AssociationRuleResponse
from backend.services.association_service import AssociationService

router = APIRouter()
service = AssociationService()


@router.post("/analyze/", response_model=AssociationRuleResponse)
async def analyze_association_rules(
    request: AssociationRuleRequest,
    background_tasks: BackgroundTasks
):
    """
    执行关联规则分析

    - **min_support**: 最小支持度 (0.0-1.0)
    - **min_confidence**: 最小置信度 (0.0-1.0)
    - **min_lift**: 最小提升度 (>= 0.0)
    - **top_n**: 返回Top N规则数量
    """
    try:
        result = await service.analyze(
            min_support=request.min_support,
            min_confidence=request.min_confidence,
            min_lift=request.min_lift,
            top_n=request.top_n
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/")
async def get_analysis_status():
    """获取分析状态"""
    return {
        "success": True,
        "status": "ready",
        "message": "关联规则分析服务正常运行"
    }
