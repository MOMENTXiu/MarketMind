"""OpenAI-compatible LLM adapter."""

from collections.abc import Callable
from typing import Any

import httpx

from backend.core.errors import ProviderError
from backend.providers.dtos import LLMRequestDTO, LLMResponseDTO


class OpenAICompatibleLLMAdapter:
    """LLM provider for OpenAI-compatible chat completion APIs."""

    def __init__(self, client_factory: Callable[..., Any] | None = None) -> None:
        self.client_factory = client_factory or httpx.AsyncClient

    async def generate_text(self, request: LLMRequestDTO) -> LLMResponseDTO:
        try:
            async with self.client_factory(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{request.base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {request.api_key or ''}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": request.model,
                        "messages": [
                            {"role": message.role, "content": message.content}
                            for message in request.messages
                        ],
                        **request.extra,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                text = payload["choices"][0]["message"]["content"].strip()
                return LLMResponseDTO(
                    text=text,
                    provider=request.provider,
                    model=request.model,
                    raw_summary={"choice_count": len(payload.get("choices", []))},
                )
        except Exception as exc:
            raise ProviderError(f"OpenAI-compatible LLM call failed: {exc}") from exc
