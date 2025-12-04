"""
大模型配置与连通性检测
"""
import json
import ssl
from pathlib import Path
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CONFIG_PATHS = [
    Path("config/llm.yaml"),
    Path("data/llm_config.json"),
]

for p in CONFIG_PATHS:
    p.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "vendor": "openai",
    "api_key": "",
    "model": "",
    "api_endpoint": ""
}


def load_config() -> Dict:
    for path in CONFIG_PATHS:
        if path.exists():
            try:
                if path.suffix.lower() == ".json":
                    return json.loads(path.read_text(encoding="utf-8"))
                # YAML 简易解析（不依赖额外库）
                cfg: Dict[str, str] = {}
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
                return {
                    "vendor": cfg.get("vendor", "openai"),
                    "api_key": cfg.get("api_key", ""),
                    "model": cfg.get("model", ""),
                    "api_endpoint": cfg.get("api_endpoint", ""),
                }
            except Exception:
                continue
    return DEFAULT_CONFIG.copy()


def save_config(cfg: Dict):
    json_path = next(p for p in CONFIG_PATHS if p.suffix == ".json")
    yaml_path = next(p for p in CONFIG_PATHS if p.suffix == ".yaml")

    json_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    # 轻量写入 YAML（无外部依赖）
    lines = [f"{k}: \"{str(v)}\"" for k, v in cfg.items() if v is not None]
    yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _chat_openai(cfg: Dict, prompt: str) -> str:
    import json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    api_key = cfg.get("api_key", "")
    model = cfg.get("model") or "gpt-4o"
    endpoint = cfg.get("api_endpoint") or "https://api.openai.com/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }).encode("utf-8")
    req = Request(
        url=endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            try:
                data = json.loads(raw)
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"]
                return raw
            except json.JSONDecodeError:
                return raw
    except HTTPError as e:
        err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        return f"（OpenAI 调用失败 HTTP {e.code}: {err_body}）"


def _chat_anthropic(cfg: Dict, prompt: str) -> str:
    import json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    api_key = cfg.get("api_key", "")
    model = cfg.get("model") or "claude-3-5-sonnet-20240620"
    endpoint = cfg.get("api_endpoint") or "https://api.anthropic.com/v1/messages"
    body = json.dumps({
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }).encode("utf-8")
    req = Request(
        url=endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "x-anthropic-version": "2023-06-01"
        },
        method="POST"
    )
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            try:
                data = json.loads(raw)
                content = data.get("content", [])
                if content and isinstance(content, list):
                    text_parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                    return "\n".join([t for t in text_parts if t])
                return raw
            except json.JSONDecodeError:
                return raw
    except HTTPError as e:
        err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        return f"（Anthropic 调用失败 HTTP {e.code}: {err_body}）"


def _chat_qwen(cfg: Dict, prompt: str) -> str:
    # 兼容OpenAI格式
    return _chat_openai(cfg, prompt)


def chat_completion(prompt: str, cfg: Optional[Dict] = None) -> str:
    """
    使用已保存的 LLM 配置进行一次对话，返回文本。
    """
    cfg = cfg or load_config()
    vendor = cfg.get("vendor", "openai")
    if not prompt:
        return ""
    try:
        if vendor == "openai":
            return _chat_openai(cfg, prompt)
        if vendor == "anthropic":
            return _chat_anthropic(cfg, prompt)
        if vendor == "qwen":
            return _chat_qwen(cfg, prompt)
        # 其他供应商按 openai 兼容模式尝试
        return _chat_openai(cfg, prompt)
    except Exception as e:
        return f"（调用大模型失败：{e}）"
