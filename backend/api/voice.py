"""
语音播报 API
"""
from fastapi import APIRouter, HTTPException
from backend.models.schemas import VoiceRequest, VoiceResponse
from backend.services.voice_service import VoiceService

router = APIRouter()
service = VoiceService()


@router.post("/generate", response_model=VoiceResponse)
async def generate_voice(request: VoiceRequest):
    """
    生成语音播报

    - **text**: 自定义文本（可选，为空则自动生成）
    - **voice**: 语音角色
    - **include_modules**: 包含的分析模块
    """
    try:
        result = await service.generate(
            text=request.text,
            voice=request.voice,
            include_modules=request.include_modules
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_voice_status():
    """获取语音服务状态"""
    return {
        "success": True,
        "status": "ready",
        "message": "语音播报服务正常运行"
    }
