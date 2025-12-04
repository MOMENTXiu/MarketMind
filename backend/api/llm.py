"""
大模型配置与连通性 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.llm import load_config, save_config, test_connection

router = APIRouter(prefix="/llm", tags=["LLM 设置"])


class LLMConfig(BaseModel):
    vendor: str
    api_key: str
    model: str
    api_endpoint: str | None = None


@router.get("/config")
async def get_config():
    cfg = load_config()
    # 返回时不暴露完整密钥
    preview = cfg.get("api_key", "")
    masked = preview[:4] + "****" + preview[-4:] if preview else ""
    return {
        "vendor": cfg.get("vendor", ""),
        "api_endpoint": cfg.get("api_endpoint", ""),
        "model": cfg.get("model", ""),
        "api_key_preview": masked,
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
