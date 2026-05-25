"""Anthropic-compatible LLM adapter."""

from collections.abc import Callable
from typing import Any

import httpx

from backend.core.errors import ProviderError
from backend.providers.dtos import LLMRequestDTO, LLMResponseDTO


class AnthropicLLMAdapter:
    """LLM provider for Anthropic-compatible messages APIs."""

    def __init__(self, client_factory: Callable[..., Any] | None = None) -> None:
        self.client_factory = client_factory or httpx.AsyncClient

    async def generate_text(self, request: LLMRequestDTO) -> LLMResponseDTO:
        try:
            system_message = next(
                (message.content for message in request.messages if message.role == "system"),
                "",
            )
            user_messages = [
                {"role": message.role, "content": message.content}
                for message in request.messages
                if message.role != "system"
            ]
            async with self.client_factory(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{request.base_url.rstrip('/')}/messages",
                    headers={
                        "x-api-key": request.api_key or "",
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": request.model,
                        "system": system_message,
                        "messages": user_messages,
                        **request.extra,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                text = payload["content"][0]["text"].strip()
                return LLMResponseDTO(
                    text=text,
                    provider=request.provider,
                    model=request.model,
                    raw_summary={"content_count": len(payload.get("content", []))},
                )
        except Exception as exc:
            raise ProviderError(f"Anthropic LLM call failed: {exc}") from exc
