"""Frontend-facing API response shape contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_customer_text_suggestion_pipeline
from backend.business.flows.retail_analysis_flow import PROJECT_STATE_MODEL_TYPE
from backend.main import app
from tests.api.conftest import IsolatedEnv


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _create_analysis_project(client: TestClient) -> str:
    response = client.post(
        "/api/analysis/projects",
        json={"name": "Frontend Matrix", "description": "retail api matrix"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["id"]
    return str(payload["data"]["id"])


def test_analysis_project_create_list_detail_delete_fields_used_by_frontend(
    client: TestClient,
    isolated_env: IsolatedEnv,
) -> None:
    project_id = _create_analysis_project(client)

    list_response = client.get("/api/analysis/projects")
    assert list_response.status_code == 200
    list_data = list_response.json()["data"]
    assert list_data["total"] == 1
    assert isinstance(list_data["projects"], list)
    assert {"id", "name", "status", "created_at", "updated_at"}.issubset(list_data["projects"][0])

    detail_response = client.get(f"/api/analysis/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()["data"]
    assert detail_data["id"] == project_id
    assert {"stage_statuses", "summary", "quality_summary", "artifact_refs"}.issubset(detail_data)

    delete_response = client.delete(f"/api/analysis/projects/{project_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True
    assert (
        isolated_env.container.analysis_models.load_model(project_id, PROJECT_STATE_MODEL_TYPE)
        is None
    )


def test_analysis_dataset_result_fields_used_by_frontend(client: TestClient) -> None:
    project_id = _create_analysis_project(client)
    fixture_path = Path("tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv")
    with fixture_path.open("rb") as dataset_file:
        upload_response = client.post(
            f"/api/analysis/projects/{project_id}/dataset",
            files={"file": ("retail.csv", dataset_file, "text/csv")},
        )
    assert upload_response.status_code == 200
    upload_data = upload_response.json()["data"]
    assert {"project_id", "status", "dataset_ref", "quality_summary"}.issubset(upload_data)
    assert upload_data["dataset_ref"]["url"].startswith("/api/analysis/projects/")
    assert "path" not in upload_data["dataset_ref"]


def test_analysis_recommendation_and_insight_fields_used_by_frontend(
    client: TestClient,
    isolated_env: IsolatedEnv,
) -> None:
    project_id = _create_analysis_project(client)
    state = isolated_env.container.analysis_models.load_model(project_id, PROJECT_STATE_MODEL_TYPE)
    assert isinstance(state, dict)
    state["recommendations"] = [
        {
            "customer_id": "C002",
            "item": "Milk",
            "score": 0.8,
            "reason": "repeat purchase",
            "score_breakdown": {"source": "runtime"},
        }
    ]
    state["marketer_insights"] = {
        "segment_value": [{"cluster_id": 1, "cluster_name": "高价值客户"}],
        "promotion_effect": [],
        "bundle_strategy": [],
        "category_strategy": [],
    }
    isolated_env.container.analysis_models.save_model(project_id, PROJECT_STATE_MODEL_TYPE, state)

    recommendations_response = client.get(
        f"/api/analysis/projects/{project_id}/recommendations",
        params={"customer_id": "C002"},
    )
    assert recommendations_response.status_code == 200
    recommendation = recommendations_response.json()["data"]["recommendations"][0]
    assert {"customer_id", "item", "score", "reason", "score_breakdown"}.issubset(recommendation)

    insights_response = client.get(f"/api/analysis/projects/{project_id}/marketer-insights")
    assert insights_response.status_code == 200
    insights_data = insights_response.json()["data"]
    assert {
        "segment_value",
        "promotion_effect",
        "bundle_strategy",
        "category_strategy",
    }.issubset(insights_data)


def test_customer_text_suggestion_fields_used_by_frontend(client: TestClient) -> None:
    class FakeCustomerTextSuggestionPipeline:
        async def generate(
            self, data: dict[str, Any], llm_config: dict[str, str]
        ) -> dict[str, Any]:
            return {
                "success": True,
                "text": "front-end customer suggestion",
                "metadata": {"provider": llm_config["provider"], "scene_type": "customer"},
            }

    app.dependency_overrides[get_customer_text_suggestion_pipeline] = (
        lambda: FakeCustomerTextSuggestionPipeline()
    )
    try:
        response = client.post(
            "/api/analysis/customer-suggestions",
            json={
                "data": {"customer_id": "C002"},
                "llm_config": {
                    "provider": "openai",
                    "baseUrl": "http://example.invalid",
                    "apiKey": "redacted",
                    "modelName": "fake",
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload == {
            "success": True,
            "text": "front-end customer suggestion",
            "metadata": {"provider": "openai", "scene_type": "customer"},
        }
        assert "audio_url" not in payload
    finally:
        app.dependency_overrides.pop(get_customer_text_suggestion_pipeline, None)
