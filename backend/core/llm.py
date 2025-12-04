"""
大模型配置与连通性检测
"""
import json
import ssl
from pathlib import Path
from typing import Dict, Optional, Iterator
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
        return "https://api.openai.com/v1/chat/completions"
    if vendor == "anthropic":
        return "https://api.anthropic.com/v1/messages"
    if vendor == "qwen":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
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


def _normalize_chat_endpoint(endpoint: str) -> str:
    if not endpoint:
        return ""
    low = endpoint.lower()
    if "chat/completions" in low:
        return endpoint
    # 补全 OpenAI 兼容路径
    if not endpoint.endswith("/"):
        endpoint = endpoint + "/"
    return endpoint + "v1/chat/completions"


def _chat_openai(cfg: Dict, prompt: str, system_prompt: str) -> str:
    import json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    api_key = cfg.get("api_key", "")
    model = cfg.get("model") or "gpt-4o"
    endpoint = _normalize_chat_endpoint(cfg.get("api_endpoint") or "https://api.openai.com/v1/chat/completions")
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
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
    return _chat_openai(cfg, prompt, "你是一个智慧助手，你要响应用户的请求")


def chat_completion(prompt: str, cfg: Optional[Dict] = None, system_prompt: str = "你是一个智慧助手，你要响应用户的请求") -> str:
    """
    使用已保存的 LLM 配置进行一次对话，返回文本。
    """
    cfg = cfg or load_config()
    vendor = cfg.get("vendor", "openai")
    if not prompt:
        return ""
    try:
        if vendor == "openai":
            return _chat_openai(cfg, prompt, system_prompt)
        if vendor == "anthropic":
            return _chat_anthropic(cfg, prompt)
        if vendor == "qwen":
            return _chat_qwen(cfg, prompt)
        # 其他供应商按 openai 兼容模式尝试
        return _chat_openai(cfg, prompt, system_prompt)
    except Exception as e:
        return f"（调用大模型失败：{e}）"


def _stream_openai(cfg: Dict, prompt: str, system_prompt: str) -> Iterator[str]:
    import json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    api_key = cfg.get("api_key", "")
    model = cfg.get("model") or "gpt-4o"
    endpoint = _normalize_chat_endpoint(cfg.get("api_endpoint") or "https://api.openai.com/v1/chat/completions")
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": True
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
        with urlopen(req, timeout=60) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                    choice = data.get("choices", [{}])[0]
                    delta = choice.get("delta") or choice.get("message") or {}
                    content = delta.get("content") or ""
                    if content:
                        yield content
                except Exception:
                    continue
    except HTTPError as e:
        err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        yield f"（OpenAI 流式失败 HTTP {e.code}: {err_body}）"
    except Exception as e:
        yield f"（OpenAI 流式异常：{e}）"


def chat_completion_stream(prompt: str, cfg: Optional[Dict] = None, system_prompt: str = "你是一个智慧助手，你要响应用户的请求") -> Iterator[str]:
    """
    返回迭代器用于流式输出；不支持流式的供应商自动退化为一次性输出。
    """
    cfg = cfg or load_config()
    vendor = cfg.get("vendor", "openai")
    if vendor == "openai":
        return _stream_openai(cfg, prompt, system_prompt)
    # fallback: 一次性输出
    def _fallback():
        yield chat_completion(prompt, cfg=cfg, system_prompt=system_prompt)
    return _fallback()
