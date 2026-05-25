"""Contract tests for speech synthesis and LLM adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from backend.infrastructure.adapters.anthropic_llm_adapter import AnthropicLLMAdapter
from backend.infrastructure.adapters.edge_tts_speech_synthesis_adapter import (
    EdgeTtsSpeechSynthesisAdapter,
)
from backend.infrastructure.adapters.openai_compatible_llm_adapter import (
    OpenAICompatibleLLMAdapter,
)
from backend.providers.dtos import LLMMessageDTO, LLMRequestDTO, SpeechSynthesisRequestDTO


class FakeCommunicate:
    def __init__(self, text: str, voice: str | None, rate: str, volume: str) -> None:
        self.text = text
        self.voice = voice
        self.rate = rate
        self.volume = volume

    async def save(self, output_path: str) -> None:
        Path(output_path).write_bytes(
            f"{self.text}|{self.voice}|{self.rate}|{self.volume}".encode()
        )


@pytest.mark.anyio
async def test_edge_tts_speech_adapter_uses_injected_factory(tmp_path: Path) -> None:
    async def fake_voice_list() -> list[dict]:
        return [{"ShortName": "fake-voice", "Locale": "zh-CN", "Gender": "Female"}]

    adapter = EdgeTtsSpeechSynthesisAdapter(
        communicate_factory=FakeCommunicate,
        voice_list_provider=fake_voice_list,
    )
    output_path = tmp_path / "audio/report.mp3"

    result = await adapter.synthesize(
        SpeechSynthesisRequestDTO(
            text="hello",
            output_path=output_path,
            voice="fake-voice",
            rate="+5%",
            volume="-5%",
        )
    )

    assert result.audio_path == output_path
    assert output_path.read_bytes() == b"hello|fake-voice|+5%|-5%"
    assert await adapter.list_voices() == [
        {"name": "fake-voice", "locale": "zh-CN", "gender": "Female"}
    ]


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeAsyncClient:
    calls: list[dict[str, Any]] = []

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> FakeResponse:
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": self.timeout})
        if url.endswith("/chat/completions"):
            return FakeResponse({"choices": [{"message": {"content": " openai text "}}]})
        return FakeResponse({"content": [{"text": " anthropic text "}]})


def make_llm_request(provider: str, base_url: str = "http://llm.local/") -> LLMRequestDTO:
    return LLMRequestDTO(
        provider=provider,
        base_url=base_url,
        model="fake-model",
        api_key="redacted",
        messages=[
            LLMMessageDTO(role="system", content="system prompt"),
            LLMMessageDTO(role="user", content="user prompt"),
        ],
        timeout_seconds=12.0,
        extra={"max_tokens": 100},
    )


@pytest.mark.anyio
async def test_openai_compatible_llm_adapter_maps_request_and_response() -> None:
    FakeAsyncClient.calls = []
    adapter = OpenAICompatibleLLMAdapter(client_factory=FakeAsyncClient)

    result = await adapter.generate_text(make_llm_request("openai"))

    assert result.text == "openai text"
    assert result.provider == "openai"
    assert result.raw_summary == {"choice_count": 1}
    call = FakeAsyncClient.calls[0]
    assert call["url"] == "http://llm.local/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer redacted"
    assert call["json"]["messages"][0] == {"role": "system", "content": "system prompt"}
    assert call["json"]["max_tokens"] == 100
    assert call["timeout"] == 12.0


@pytest.mark.anyio
async def test_anthropic_llm_adapter_maps_request_and_response() -> None:
    FakeAsyncClient.calls = []
    adapter = AnthropicLLMAdapter(client_factory=FakeAsyncClient)

    result = await adapter.generate_text(make_llm_request("claude"))

    assert result.text == "anthropic text"
    assert result.provider == "claude"
    assert result.raw_summary == {"content_count": 1}
    call = FakeAsyncClient.calls[0]
    assert call["url"] == "http://llm.local/messages"
    assert call["headers"]["x-api-key"] == "redacted"
    assert call["json"]["system"] == "system prompt"
    assert call["json"]["messages"] == [{"role": "user", "content": "user prompt"}]
