"""
大模型配置与连通性 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import asyncio

from backend.core.llm import load_config, save_config, test_connection

router = APIRouter(prefix="/llm", tags=["LLM 设置"])


class LLMConfig(BaseModel):
    vendor: str
    api_key: str
    model: str
    api_endpoint: str | None = None


class ChatRequest(BaseModel):
    prompt: str


@router.get("/config")
async def get_config():
    cfg = load_config()
    return {
        "vendor": cfg.get("vendor", ""),
        "api_endpoint": cfg.get("api_endpoint", ""),
        "model": cfg.get("model", ""),
        "api_key": cfg.get("api_key", ""),
    }


@router.post("/config")
async def set_config(body: LLMConfig):
    try:
        save_config(body.model_dump())
        return {"success": True, "message": "配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")


@router.post("/test")
async def test_llm(body: LLMConfig | None = None):
    cfg = body.model_dump() if body else load_config()
    result = test_connection(cfg)
    if result.get("success"):
        return result
    raise HTTPException(status_code=500, detail=result.get("message", "测试失败"))


@router.post("/chat")
async def chat(body: ChatRequest):
    """
    原型聊天接口（流式）。目前为占位回声流，如需真实大模型可在此对接外部API。
    """
    prompt = body.prompt or ""

    async def streamer():
        yield "助手: "
        # 模拟分段回复
        for chunk in ["收到你的消息：", prompt[:50], " …（演示流式输出）"]:
            await asyncio.sleep(0.1)
            yield chunk

    return StreamingResponse(streamer(), media_type="text/plain")
