"""
大模型配置与连通性检测
"""
import json
import ssl
from pathlib import Path
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CONFIG_PATH = Path("data/llm_config.json")
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "vendor": "openai",
    "api_key": "",
    "model": "",
    "api_endpoint": ""
}


def load_config() -> Dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(cfg: Dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_endpoint(vendor: str) -> str:
    if vendor == "openai":
        return "https://api.openai.com/v1/models"
    if vendor == "anthropic":
        return "https://api.anthropic.com/v1/models"
    if vendor == "qwen":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1/models"
    return ""


def _build_request(cfg: Dict) -> Optional[Request]:
    vendor = cfg.get("vendor", "openai")
    api_key = cfg.get("api_key", "")
    endpoint = cfg.get("api_endpoint") or _default_endpoint(vendor)
    headers = {}

    if not endpoint:
        return None

    if vendor == "openai":
        headers["Authorization"] = f"Bearer {api_key}"
    elif vendor == "anthropic":
        headers["x-api-key"] = api_key
        headers["x-anthropic-version"] = "2023-06-01"
    elif vendor == "qwen":
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        # custom: 尝试 Bearer，如果没有密钥则不加
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    return Request(url=endpoint, headers=headers, method="GET")


def test_connection(cfg: Optional[Dict] = None) -> Dict:
    cfg = cfg or load_config()
    req = _build_request(cfg)
    if not req:
        return {"success": False, "message": "缺少 API 地址，请填写供应商或自定义地址"}

    try:
        context = ssl.create_default_context()
        with urlopen(req, timeout=8, context=context) as resp:
            return {
                "success": True,
                "status": resp.status,
                "message": f"连接成功，HTTP {resp.status}"
            }
    except HTTPError as e:
        return {"success": False, "status": e.code, "message": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"success": False, "message": f"网络错误: {e.reason}"}
    except Exception as e:
        return {"success": False, "message": f"连接异常: {e}"}
