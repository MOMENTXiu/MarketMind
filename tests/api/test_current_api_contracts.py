"""Smoke tests for current public API contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_ai_voice_broadcast_pipeline, get_voice_synthesis_pipeline
from backend.core.errors import NotFoundError
from backend.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_root_and_health_contracts(client: TestClient) -> None:
    root_response = client.get("/")
    assert root_response.status_code == 200
    assert root_response.json() == {
        "message": "MarketMind API is running",
        "version": "1.0.0",
        "docs": "/api/docs",
    }

    health_response = client.get("/api/health/")
    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "healthy",
        "service": "MarketMind Backend",
    }


def test_retired_analysis_routes_are_not_public(client: TestClient) -> None:
    schema_paths = set(app.openapi()["paths"])
    assert not any(path.startswith("/api/projects") for path in schema_paths)
    assert not any(path.startswith("/api/recommend") for path in schema_paths)
    assert not any(path.startswith("/api/association") for path in schema_paths)

    retired_requests = [
        client.get("/api/projects/"),
        client.get("/api/projects/missing/"),
        client.get("/api/recommend/item/?item=Milk"),
        client.post("/api/recommend/calculate/", json={"item": "Milk"}),
        client.post("/api/association/analyze/", json={"top_n": 3}),
        client.get("/api/association/status/"),
    ]
    assert {response.status_code for response in retired_requests} == {404}


def test_voice_contracts(client: TestClient) -> None:
    class FakeVoicePipeline:
        async def synthesize(
            self,
            text: str,
            voice: str | None = None,
            rate: str | None = None,
            volume: str | None = None,
        ) -> dict[str, Any]:
            return {
                "success": True,
                "audio_url": f"/outputs/audio/tts_{abs(hash(text)) % 1000}.mp3",
                "text": text,
            }

    app.dependency_overrides[get_voice_synthesis_pipeline] = lambda: FakeVoicePipeline()
    try:
        tts_response = client.post("/api/voice/tts/", json={"text": "hello"})
        assert tts_response.status_code == 200
        tts_payload = tts_response.json()
        assert tts_payload["success"] is True
        assert tts_payload["audio_url"].startswith("/outputs/audio/tts_")
        assert tts_payload["text"] == "hello"

        voice_response = client.post("/api/voice/generate/", json={"text": "custom voice"})
        assert voice_response.status_code == 200
        assert voice_response.json()["audio_url"] == "/outputs/audio/temp.mp3"
    finally:
        app.dependency_overrides.pop(get_voice_synthesis_pipeline, None)


def test_ai_voice_contracts(client: TestClient) -> None:
    class FakeAIVoicePipeline:
        async def broadcast(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "success": True,
                "text": "generated broadcast",
                "audio_url": "/api/ai-voice/audio/contract-broadcast.mp3/",
            }

        async def synthesize_tts(self, text: str, **kwargs: Any) -> dict[str, Any]:
            return {
                "success": True,
                "audio_url": "/api/ai-voice/audio/contract-tts.mp3/",
            }

        def resolve_audio_path(self, filename: str) -> Path:
            if filename == "marketmind-contract-audio.mp3":
                return Path("/tmp/marketmind-contract-audio.mp3")
            raise NotFoundError("音频文件不存在")

    app.dependency_overrides[get_ai_voice_broadcast_pipeline] = lambda: FakeAIVoicePipeline()
    try:
        broadcast_response = client.post(
            "/api/ai-voice/broadcast/",
            json={
                "data": {"metric": 1},
                "llm_config": {
                    "provider": "openai",
                    "baseUrl": "http://example.invalid",
                    "apiKey": "redacted",
                    "modelName": "fake",
                },
                "scene_type": "summary",
                "tts_config": None,
            },
        )
        assert broadcast_response.status_code == 200
        assert broadcast_response.json() == {
            "success": True,
            "text": "generated broadcast",
            "audio_url": "/api/ai-voice/audio/contract-broadcast.mp3/",
        }

        tts_response = client.post("/api/tts/", json={"text": "hello"})
        assert tts_response.status_code == 200
        assert tts_response.json() == {
            "success": True,
            "audio_url": "/api/ai-voice/audio/contract-tts.mp3/",
        }

        missing_audio_response = client.get("/api/ai-voice/audio/missing-contract-audio.mp3/")
        assert missing_audio_response.status_code == 404
        assert missing_audio_response.json()["detail"] == "音频文件不存在"

        audio_path = Path("/tmp/marketmind-contract-audio.mp3")
        audio_path.write_bytes(b"fake mp3")
        try:
            audio_response = client.get("/api/ai-voice/audio/marketmind-contract-audio.mp3/")
            assert audio_response.status_code == 200
            assert audio_response.headers["content-type"] == "audio/mpeg"
            assert audio_response.content == b"fake mp3"
        finally:
            audio_path.unlink(missing_ok=True)
    finally:
        app.dependency_overrides.pop(get_ai_voice_broadcast_pipeline, None)
