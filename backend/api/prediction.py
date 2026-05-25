"""
销售预测 API
"""

from fastapi import APIRouter, HTTPException

from backend.models.schemas import PredictionRequest, PredictionResponse
from backend.services.prediction_service import PredictionService

router = APIRouter()
service = PredictionService()


@router.post("/forecast/", response_model=PredictionResponse)
async def forecast_sales(request: PredictionRequest):
    """
    执行销售预测

    - **forecast_weeks**: 预测未来几周 (1-52)
    - **model_type**: 模型类型 (ridge/random_forest/gradient_boosting)
    """
    try:
        result = await service.forecast(
            forecast_weeks=request.forecast_weeks, model_type=request.model_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/")
async def get_prediction_status():
    """获取预测服务状态"""
    return {"success": True, "status": "ready", "message": "销售预测服务正常运行"}
