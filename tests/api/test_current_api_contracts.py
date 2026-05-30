"""Smoke tests for current public API contracts."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_customer_text_suggestion_pipeline
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
    body = health_response.json()
    assert body["service"] == "MarketMind Backend"
    assert body["status"] in ("healthy", "degraded")
    assert "version" in body
    assert "components" in body


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


def test_customer_text_suggestion_contract(client: TestClient) -> None:
    class FakeCustomerTextSuggestionPipeline:
        async def generate(
            self, data: dict[str, Any], llm_config: dict[str, str]
        ) -> dict[str, Any]:
            return {
                "success": True,
                "text": "generated customer suggestion",
                "metadata": {"provider": llm_config["provider"]},
            }

    app.dependency_overrides[get_customer_text_suggestion_pipeline] = (
        lambda: FakeCustomerTextSuggestionPipeline()
    )
    try:
        response = client.post(
            "/api/analysis/customer-suggestions",
            json={
                "data": {"metric": 1},
                "llm_config": {
                    "provider": "openai",
                    "baseUrl": "http://example.invalid",
                    "apiKey": "redacted",
                    "modelName": "fake",
                },
            },
        )
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "text": "generated customer suggestion",
            "metadata": {"provider": "openai"},
        }
        assert "audio_url" not in response.json()
    finally:
        app.dependency_overrides.pop(get_customer_text_suggestion_pipeline, None)
