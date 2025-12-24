"""
AI 语音播报 API
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from backend.services.ai_voice_service import AIVoiceService

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


router = APIRouter()


class VoiceBroadcastRequest(BaseModel):
    data: Dict[str, Any]
    llm_config: Dict[str, str]
    scene_type: str = "summary"
    tts_config: Optional[Dict[str, str]] = None


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: Optional[str] = None
    volume: Optional[str] = None


@router.post("/ai-voice/broadcast/")
async def generate_voice_broadcast(request: VoiceBroadcastRequest):
    """
    生成 AI 语音播报（LLM + TTS 完整流程）

    Request Body:
        - data: 算法数据（JSON）
        - llm_config: LLM 配置 {provider, baseUrl, apiKey, modelName}
        - scene_type: 场景类型 (clustering, association, prediction, summary)
        - tts_config: TTS 配置 {voice, rate, volume}（可选）

    Response:
        - success: 是否成功
        - text: LLM 生成的播报文案
        - audio_url: 音频文件访问地址
    """
    logger.info("=" * 80)
    logger.info("[AI Voice Broadcast] 收到AI语音播报请求")
    logger.info(f"[AI Voice Broadcast] 场景类型: {request.scene_type}")
    logger.info(f"[AI Voice Broadcast] LLM配置: provider={request.llm_config.get('provider')}, model={request.llm_config.get('modelName')}")
    logger.info(f"[AI Voice Broadcast] TTS配置: {request.tts_config}")

    result = await AIVoiceService.generate_voice_broadcast(
        data=request.data,
        llm_config=request.llm_config,
        scene_type=request.scene_type,
        tts_config=request.tts_config
    )

    logger.info(f"[AI Voice Broadcast] AI Voice Service 处理结果: success={result['success']}")

    if not result["success"]:
        logger.error(f"[AI Voice Broadcast] 语音生成失败: {result.get('error')}")
        raise HTTPException(status_code=500, detail=result.get("error", "语音生成失败"))

    # 转换为相对 URL
    audio_path = result["audio_path"]
    audio_url = f"/api/ai-voice/audio/{Path(audio_path).name}/"  # Add trailing slash
    logger.info(f"[AI Voice Broadcast] 生成的音频URL: {audio_url}")
    logger.info(f"[AI Voice Broadcast] LLM生成的文本: {result['text'][:100]}...")

    response = {
        "success": True,
        "text": result["text"],
        "audio_url": audio_url
    }
    logger.info(f"[AI Voice Broadcast] 返回响应")
    logger.info("=" * 80)
    return response


@router.post("/tts/")
async def text_to_speech(request: TTSRequest):
    """
    纯 TTS 服务（不调用 LLM）

    Request Body:
        - text: 要转换的文本
        - voice: 语音模型（可选）
        - rate: 语速（可选）
        - volume: 音量（可选）

    Response:
        - audio_url: 音频文件访问地址
    """
    try:
        audio_path = await AIVoiceService.text_to_speech(
            request.text,
            voice=request.voice,
            rate=request.rate,
            volume=request.volume
        )
        audio_url = f"/api/ai-voice/audio/{Path(audio_path).name}/"  # Add trailing slash

        return {
            "success": True,
            "audio_url": audio_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 失败: {str(e)}")


@router.get("/ai-voice/audio/{filename}/")
async def get_audio_file(filename: str):
    """
    获取音频文件

    Args:
        filename: 音频文件名

    Returns:
        音频文件流
    """
    # 先检查临时目录
    temp_path = Path(f"/tmp/{filename}")
    if temp_path.exists():
        return FileResponse(
            temp_path,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )

    # 再检查数据目录
    data_path = Path(f"backend/data/audio/{filename}")
    if data_path.exists():
        return FileResponse(
            data_path,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )

    raise HTTPException(status_code=404, detail="音频文件不存在")
