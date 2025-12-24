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
import logging

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()
service = VoiceService()
tts_service = TTSService(voice="zh-CN-XiaoxiaoNeural")

class SimpleTTSRequest(BaseModel):
    text: str
    voice: str | None = "zh-CN-XiaoxiaoNeural"
    rate: str | None = "+0%"
    volume: str | None = "+0%"

@router.post("/tts/")
async def text_to_speech(request: SimpleTTSRequest):
    """
    极简 TTS 接口：文本 -> 音频访问路径
    支持自定义语音、语速和音量
    """
    logger.info("=" * 80)
    logger.info("[TTS Backend] 收到 TTS 请求")
    logger.info(f"[TTS Backend] 请求参数: text={request.text[:50]}..., voice={request.voice}, rate={request.rate}, volume={request.volume}")

    try:
        file_id = uuid4().hex
        logger.info(f"[TTS Backend] 生成文件ID: {file_id}")

        output_dir = Path("outputs/audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[TTS Backend] 输出目录: {output_dir.absolute()}")

        filename = f"tts_{file_id}.mp3"
        filepath = output_dir / filename
        logger.info(f"[TTS Backend] 输出文件路径: {filepath.absolute()}")

        logger.info(f"[TTS Backend] 调用 TTS 服务进行语音合成...")
        await tts_service.synthesize(
            request.text,
            str(filepath),
            voice=request.voice,
            rate=request.rate,
            volume=request.volume
        )
        logger.info(f"[TTS Backend] TTS 合成完成")

        # 检查文件是否生成
        if filepath.exists():
            file_size = filepath.stat().st_size
            logger.info(f"[TTS Backend] 音频文件已生成: {filepath}, 大小: {file_size} bytes")
        else:
            logger.error(f"[TTS Backend] 音频文件未生成: {filepath}")
            raise Exception("音频文件生成失败")

        audio_url = f"/outputs/audio/{filename}"
        logger.info(f"[TTS Backend] 返回音频 URL: {audio_url}")

        response = {
            "success": True,
            "audio_url": audio_url,
            "text": request.text
        }
        logger.info(f"[TTS Backend] 响应数据: {response}")
        logger.info("=" * 80)
        return response
    except Exception as e:
        logger.error(f"[TTS Backend] TTS 合成失败: {str(e)}", exc_info=True)
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"TTS 合成失败: {str(e)}")

@router.post("/generate/", response_model=VoiceResponse)
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


@router.get("/status/")
async def get_voice_status():
    """获取语音服务状态"""
    return {
        "success": True,
        "status": "ready",
        "message": "语音播报服务正常运行"
    }
