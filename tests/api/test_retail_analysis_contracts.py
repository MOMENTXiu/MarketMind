"""Retail V2 API contracts for the planned `/api/analysis` surface."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.business.flows.retail_analysis_state import public_ref
from backend.main import app
from tests.api.conftest import IsolatedEnv

VALID_PROJECT_STATUSES = {"queued", "processing", "completed", "failed"}
VALID_STAGE_STATUSES = {"queued", "processing", "completed", "failed", "skipped"}
REQUIRED_STAGE_NAMES = {
    "dataset_preparation",
    "feature_engineering",
    "segmentation",
    "association",
    "recommendation",
    "marketer_insights",
    "report",
}
LOCAL_ARTIFACT_MARKERS = (
    "/Users/",
    "analysis/output",
    "backend/data",
    "outputs/",
    "data/projects",
)


@pytest.fixture()
def client(isolated_env: IsolatedEnv) -> TestClient:
    return TestClient(app)


def assert_success_payload(payload: dict[str, Any]) -> dict[str, Any]:
    assert payload["success"] is True
    assert isinstance(payload["data"], dict)
    return payload["data"]


def assert_error_payload(payload: dict[str, Any]) -> None:
    assert "detail" in payload or {"error", "message"}.issubset(payload)


def assert_stage_contract(stage: dict[str, Any]) -> None:
    assert {"stage", "status", "error", "artifact_refs"}.issubset(stage)
    assert stage["stage"] in REQUIRED_STAGE_NAMES
    assert stage["status"] in VALID_STAGE_STATUSES
    assert isinstance(stage["artifact_refs"], list)


def assert_artifact_ref_contract(artifact: dict[str, Any]) -> None:
    assert {"id", "type", "name", "url", "metadata"}.issubset(artifact)
    assert artifact["type"] in {"table", "figure", "markdown", "json", "model"}
    assert isinstance(artifact["metadata"], dict)
    assert "path" not in artifact
    assert not any(marker in artifact["url"] for marker in LOCAL_ARTIFACT_MARKERS)
    assert artifact["url"].startswith("/api/analysis/projects/")


def assert_ref_is_path_free(ref: dict[str, Any]) -> None:
    assert "path" not in ref
    assert "storage_key" not in ref
    assert not any(marker in str(ref) for marker in LOCAL_ARTIFACT_MARKERS)


def create_retail_project(client: TestClient) -> str:
    response = client.post(
        "/api/analysis/projects",
        json={"name": "Retail V2 Contract", "description": "API contract anchor"},
    )
    assert response.status_code == 201

    data = assert_success_payload(response.json())
    assert data["name"] == "Retail V2 Contract"
    assert data["status"] == "queued"
    assert isinstance(data["id"], str) and data["id"]
    assert isinstance(data["stage_statuses"], list)
    assert {stage["stage"] for stage in data["stage_statuses"]} == REQUIRED_STAGE_NAMES
    for stage in data["stage_statuses"]:
        assert_stage_contract(stage)
    return data["id"]


def parse_sse_data(response_text: str) -> dict[str, Any]:
    data_line = next(line for line in response_text.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert isinstance(payload, dict)
    return payload


def upload_retail_dataset(client: TestClient, project_id: str) -> dict[str, Any]:
    fixture_path = Path("tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv")
    with fixture_path.open("rb") as dataset_file:
        response = client.post(
            f"/api/analysis/projects/{project_id}/dataset",
            files={"file": (fixture_path.name, dataset_file, "text/csv")},
        )
    assert response.status_code == 200

    data = assert_success_payload(response.json())
    assert data["project_id"] == project_id
    assert data["status"] == "queued"
    assert {"dataset_ref", "quality_summary"}.issubset(data)
    assert isinstance(data["quality_summary"], dict)
    assert not any(marker in str(data["dataset_ref"]) for marker in LOCAL_ARTIFACT_MARKERS)
    return data


def replace_retail_project_state(
    isolated_env: IsolatedEnv,
    project_id: str,
    **changes: Any,
) -> None:
    state = isolated_env.container.retail_analysis_state.get_state(project_id)
    assert state is not None
    isolated_env.container.retail_analysis_state.save_state(replace(state, **changes))


def test_create_retail_analysis_project_contract(client: TestClient) -> None:
    project_id = create_retail_project(client)

    list_response = client.get("/api/analysis/projects")
    assert list_response.status_code == 200
    list_data = assert_success_payload(list_response.json())
    assert list_data["total"] == 1
    assert list_data["projects"][0]["id"] == project_id


def test_retail_project_events_endpoint_streams_sse_contract(client: TestClient) -> None:
    project_id = create_retail_project(client)

    response = client.get(f"/api/analysis/projects/{project_id}/events")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "id:" in response.text
    assert "event:" in response.text
    assert "retry:" in response.text
    assert "data:" in response.text

    event = parse_sse_data(response.text)
    assert event["resource"] == "retail_project"
    assert event["project_id"] == project_id
    assert event["fallback_url"] == f"/api/analysis/projects/{project_id}"
    assert event["payload"]["project_id"] == project_id
    assert event["payload"]["fallback_url"] == f"/api/analysis/projects/{project_id}"


def test_delete_retail_analysis_project_contract(client: TestClient) -> None:
    project_id = create_retail_project(client)
    delete_response = client.delete(f"/api/analysis/projects/{project_id}")
    assert delete_response.status_code == 200

    delete_data = assert_success_payload(delete_response.json())
    assert delete_data["project_id"] == project_id
    assert delete_data["deleted"] is True

    missing_response = client.get(f"/api/analysis/projects/{project_id}")
    assert missing_response.status_code == 404

    list_response = client.get("/api/analysis/projects")
    assert list_response.status_code == 200
    assert assert_success_payload(list_response.json())["total"] == 0


def test_retired_routes_are_absent_from_openapi(client: TestClient) -> None:
    schema_paths = set(app.openapi()["paths"])
    assert not any(path.startswith("/api/projects") for path in schema_paths)
    assert not any(path.startswith("/api/recommend") for path in schema_paths)
    assert not any(path.startswith("/api/association") for path in schema_paths)
    assert client.get("/api/projects/").status_code == 404
    assert client.get("/api/recommend/item/?item=Milk").status_code == 404
    assert client.post("/api/association/analyze/", json={"top_n": 3}).status_code == 404


def test_dataset_upload_and_run_status_contract(client: TestClient) -> None:
    project_id = create_retail_project(client)
    upload_retail_dataset(client, project_id)

    run_response = client.post(f"/api/analysis/projects/{project_id}/run")
    assert run_response.status_code == 202

    run_data = assert_success_payload(run_response.json())
    assert run_data["project_id"] == project_id
    assert run_data["status"] == "processing"
    assert isinstance(run_data["job_id"], str) and run_data["job_id"]
    assert isinstance(run_data["trace_id"], str) and run_data["trace_id"]

    status_response = client.get(f"/api/analysis/projects/{project_id}")
    assert status_response.status_code == 200

    status_data = assert_success_payload(status_response.json())
    assert status_data["id"] == project_id
    assert status_data["status"] in VALID_PROJECT_STATUSES
    assert isinstance(status_data["summary"], dict)
    for stage in status_data["stage_statuses"]:
        assert_stage_contract(stage)


def test_artifact_refs_contract(client: TestClient) -> None:
    project_id = create_retail_project(client)
    response = client.get(f"/api/analysis/projects/{project_id}/artifacts")
    assert response.status_code == 200

    data = assert_success_payload(response.json())
    assert data["project_id"] == project_id
    assert isinstance(data["artifacts"], list)
    for artifact in data["artifacts"]:
        assert_artifact_ref_contract(artifact)


def test_ref_urls_are_dereferenceable_metadata(
    client: TestClient,
    isolated_env: IsolatedEnv,
) -> None:
    project_id = create_retail_project(client)
    upload_data = upload_retail_dataset(client, project_id)
    dataset_ref = upload_data["dataset_ref"]

    dataset_response = client.get(dataset_ref["url"])
    assert dataset_response.status_code == 200
    dataset_data = assert_success_payload(dataset_response.json())
    assert dataset_data == dataset_ref
    assert_ref_is_path_free(dataset_data)

    artifacts_response = client.get(f"/api/analysis/projects/{project_id}/artifacts")
    artifact = assert_success_payload(artifacts_response.json())["artifacts"][0]
    assert ":" in artifact["id"]

    artifact_response = client.get(artifact["url"])
    assert artifact_response.status_code == 200
    artifact_data = assert_success_payload(artifact_response.json())
    assert artifact_data == artifact
    assert_ref_is_path_free(artifact_data)

    model_ref = isolated_env.container.analysis_models.save_model(
        project_id,
        "retail_contract_model",
        {"ready": True},
    )
    state = isolated_env.container.retail_analysis_state.get_state(project_id)
    assert state is not None
    replace_retail_project_state(
        isolated_env,
        project_id,
        artifact_refs=[*list(state.artifact_refs), public_ref(model_ref)],
    )

    model_response = client.get(model_ref.url)
    assert model_response.status_code == 200
    model_data = assert_success_payload(model_response.json())
    assert model_data["id"] == model_ref.id
    assert model_data["type"] == "model"
    assert_ref_is_path_free(model_data)


def test_artifact_payload_endpoint_returns_path_free_rows(
    client: TestClient,
    isolated_env: IsolatedEnv,
) -> None:
    project_id = create_retail_project(client)
    artifact_ref = isolated_env.container.analysis_artifacts.save_table(
        project_id,
        "frontend_rows.csv",
        pd.DataFrame([{"item": "Milk", "score": 0.75, "missing": float("nan")}]),
    )
    state = isolated_env.container.retail_analysis_state.get_state(project_id)
    assert state is not None
    replace_retail_project_state(
        isolated_env,
        project_id,
        artifact_refs=[*list(state.artifact_refs), public_ref(artifact_ref)],
    )

    response = client.get(f"{artifact_ref.url}/payload")
    assert response.status_code == 200
    data = assert_success_payload(response.json())

    assert data["project_id"] == project_id
    assert data["artifact"]["id"] == artifact_ref.id
    assert data["payload_type"] == "table"
    assert data["rows"] == [{"item": "Milk", "score": 0.75, "missing": None}]
    assert data["payload"] is None
    assert data["content"] is None
    assert_ref_is_path_free(data["artifact"])
    assert not any(marker in str(data["rows"]) for marker in LOCAL_ARTIFACT_MARKERS)


def test_unsupported_artifact_payload_returns_error(
    client: TestClient,
    isolated_env: IsolatedEnv,
) -> None:
    project_id = create_retail_project(client)
    artifact_ref = isolated_env.container.analysis_artifacts.save_figure(
        project_id,
        "chart.png",
        b"not-a-real-png",
    )
    state = isolated_env.container.retail_analysis_state.get_state(project_id)
    assert state is not None
    replace_retail_project_state(
        isolated_env,
        project_id,
        artifact_refs=[*list(state.artifact_refs), public_ref(artifact_ref)],
    )

    response = client.get(f"{artifact_ref.url}/payload")
    assert response.status_code == 400
    assert_error_payload(response.json())


def test_result_endpoint_contracts(client: TestClient) -> None:
    project_id = create_retail_project(client)

    recommendations_response = client.get(
        f"/api/analysis/projects/{project_id}/recommendations",
        params={"customer_id": "C001", "top_k": 5},
    )
    assert recommendations_response.status_code == 200

    recommendations_data = assert_success_payload(recommendations_response.json())
    assert recommendations_data["project_id"] == project_id
    assert isinstance(recommendations_data["recommendations"], list)
    for recommendation in recommendations_data["recommendations"]:
        assert {"item", "score", "reason", "score_breakdown"}.issubset(recommendation)
        assert isinstance(recommendation["score_breakdown"], dict)

    insights_response = client.get(f"/api/analysis/projects/{project_id}/marketer-insights")
    assert insights_response.status_code == 200

    insights_data = assert_success_payload(insights_response.json())
    assert insights_data["project_id"] == project_id
    assert {
        "segment_value",
        "promotion_effect",
        "bundle_strategy",
        "category_strategy",
    }.issubset(insights_data)


def test_error_contracts(client: TestClient) -> None:
    invalid_create = client.post("/api/analysis/projects", json={"name": ""})
    assert invalid_create.status_code in {400, 422}
    assert_error_payload(invalid_create.json())

    missing_project = client.get("/api/analysis/projects/missing-project")
    assert missing_project.status_code == 404
    assert_error_payload(missing_project.json())

    wrong_file = client.post(
        "/api/analysis/projects/project-id/dataset",
        files={"file": ("dataset.txt", b"not,a,retail,csv", "text/plain")},
    )
    assert wrong_file.status_code in {400, 422}
    assert_error_payload(wrong_file.json())
