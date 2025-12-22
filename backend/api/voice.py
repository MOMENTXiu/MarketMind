"""
语音播报 API
"""
from fastapi import APIRouter, HTTPException
from backend.models.schemas import VoiceRequest, VoiceResponse
from backend.services.voice_service import VoiceService

from pydantic import BaseModel
from uuid import uuid4
from backend.services.tts_service import TTSService
from pathlib import Path

router = APIRouter()
service = VoiceService()
tts_service = TTSService(voice="zh-CN-YunxiNeural")

class SimpleTTSRequest(BaseModel):
    text: str

@router.post("/tts")
async def text_to_speech(request: SimpleTTSRequest):
    """
    极简 TTS 接口：文本 -> 音频访问路径
    """
    try:
        file_id = uuid4().hex
        output_dir = Path("outputs/audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"tts_{file_id}.mp3"
        filepath = output_dir / filename
        
        await tts_service.synthesize(request.text, str(filepath))
        
        return {
            "success": True,
            "audio_url": f"/outputs/audio/{filename}",
            "text": request.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 合成失败: {str(e)}")

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
