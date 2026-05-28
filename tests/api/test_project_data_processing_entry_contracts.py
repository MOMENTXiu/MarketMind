"""Project-entry Data Processing API contract tests.

Covers the real product path:
  POST /api/analysis/projects  (with analysis_kind="data_processing")
    -> POST /api/analysis/projects/{id}/dataset
    -> POST /api/analysis/projects/{id}/regularize
    -> GET  /api/analysis/projects/{id}
    -> GET  /api/analysis/projects
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.api.conftest import IsolatedEnv

VALID_JOB_STATUSES = {"queued", "processing", "completed", "failed", "needs_review"}
VALID_STAGE_STATUSES = {"queued", "processing", "completed", "skipped", "failed", "needs_review"}
REQUIRED_STAGE_NAMES = {
    "dataset_regularization",
    "overview",
    "profile_segmentation",
    "association",
    "recommendation",
    "promotion",
    "summary",
}
DP_PROJECT_MARKER_STAGES = {"dataset_regularization"}


@pytest.fixture()
def client(isolated_env: IsolatedEnv) -> TestClient:
    return TestClient(app)


def assert_success_payload(payload: dict[str, Any]) -> dict[str, Any]:
    assert payload["success"] is True
    assert isinstance(payload["data"], dict)
    return payload["data"]


def create_dp_project(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/analysis/projects",
        json={
            "name": "DP Entry Contract",
            "description": "Testing the project-based DP entry",
            "analysis_kind": "data_processing",
        },
    )
    assert response.status_code == 201
    data = assert_success_payload(response.json())
    assert data["analysis_kind"] == "data_processing"
    assert data["id"]
    assert data["status"] == "queued"
    stage_names = {s["stage"] for s in data.get("stage_statuses", []) if isinstance(s, dict)}
    assert stage_names == REQUIRED_STAGE_NAMES
    return data


def upload_dataset_to_project(
    client: TestClient, project_id: str, fixture_name: str = "mini_retail.csv"
) -> dict[str, Any]:
    fixture_path = Path("tests/fixtures/data_processing") / fixture_name
    with fixture_path.open("rb") as dataset_file:
        response = client.post(
            f"/api/analysis/projects/{project_id}/dataset",
            files={"file": (fixture_path.name, dataset_file, "text/csv")},
        )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = assert_success_payload(response.json())
    assert data["project_id"] == project_id
    assert data["job_id"]
    return data


def test_create_dp_project_includes_analysis_kind(client: TestClient) -> None:
    project = create_dp_project(client)
    assert project["analysis_kind"] == "data_processing"


def test_dp_project_upload_does_not_trigger_retail_v2_validation(client: TestClient) -> None:
    project = create_dp_project(client)
    project_id = project["id"]

    # Upload a CSV that would *fail* the old Retail V2 17-column validation
    fixture_path = Path("tests/fixtures/data_processing/mini_retail.csv")
    with fixture_path.open("rb") as dataset_file:
        response = client.post(
            f"/api/analysis/projects/{project_id}/dataset",
            files={"file": (fixture_path.name, dataset_file, "text/csv")},
        )

    assert response.status_code == 200, f"Unexpected upload failure: {response.text}"
    data = assert_success_payload(response.json())
    assert data["project_id"] == project_id
    assert data["job_id"]

    # The response must NOT contain the old Retail V2 error
    error_text = response.text.lower()
    assert "retail v2 raw sales dataset missing columns" not in error_text
    assert "missing columns" not in error_text or "retail v2" not in error_text


def test_dp_project_upload_links_job_to_project(client: TestClient) -> None:
    project = create_dp_project(client)
    project_id = project["id"]

    upload_data = upload_dataset_to_project(client, project_id)
    job_id = upload_data["job_id"]

    # Verify the project detail reflects the linked job
    detail_response = client.get(f"/api/analysis/projects/{project_id}")
    assert detail_response.status_code == 200
    detail = assert_success_payload(detail_response.json())
    assert detail["analysis_kind"] == "data_processing"
    assert detail["job_id"] == job_id


def test_dp_project_regularize_contract(client: TestClient) -> None:
    project = create_dp_project(client)
    project_id = project["id"]
    upload_dataset_to_project(client, project_id)

    reg_response = client.post(f"/api/analysis/projects/{project_id}/regularize")
    assert reg_response.status_code == 200
    reg_data = assert_success_payload(reg_response.json())
    assert reg_data["status"] in VALID_JOB_STATUSES
    assert isinstance(reg_data.get("quality"), dict)
    assert isinstance(reg_data.get("capability"), dict)
    assert isinstance(reg_data.get("output_refs"), list)

    for stage in reg_data.get("stages", []):
        assert {"stage", "status", "error", "artifact_refs"}.issubset(stage)
        assert stage["stage"] in REQUIRED_STAGE_NAMES
        assert stage["status"] in VALID_STAGE_STATUSES

    reg_stage = next(
        (s for s in reg_data.get("stages", []) if s.get("stage") == "dataset_regularization"),
        None,
    )
    assert reg_stage is not None
    assert reg_stage["status"] in {"completed", "needs_review"}


def test_dp_project_detail_reflects_job_state(client: TestClient) -> None:
    project = create_dp_project(client)
    project_id = project["id"]
    upload_data = upload_dataset_to_project(client, project_id)
    job_id = upload_data["job_id"]

    client.post(f"/api/analysis/projects/{project_id}/regularize")

    detail_response = client.get(f"/api/analysis/projects/{project_id}")
    assert detail_response.status_code == 200
    detail = assert_success_payload(detail_response.json())

    assert detail["analysis_kind"] == "data_processing"
    assert detail["job_id"] == job_id
    # stage_statuses should reflect DP job state, not old Retail V2 stages
    stage_names = {s["stage"] for s in detail.get("stage_statuses", []) if isinstance(s, dict)}
    assert "dataset_regularization" in stage_names
    assert "dataset_preparation" not in stage_names


def test_dp_project_list_reflects_job_state(client: TestClient) -> None:
    project = create_dp_project(client)
    project_id = project["id"]
    upload_data = upload_dataset_to_project(client, project_id)
    job_id = upload_data["job_id"]

    client.post(f"/api/analysis/projects/{project_id}/regularize")

    list_response = client.get("/api/analysis/projects")
    assert list_response.status_code == 200
    list_data = assert_success_payload(list_response.json())

    found = next((p for p in list_data.get("projects", []) if p.get("id") == project_id), None)
    assert found is not None, "DP project should appear in list"
    assert found.get("analysis_kind") == "data_processing"
    assert found.get("job_id") == job_id
    # List should also reflect merged DP stage state
    stage_names = {s["stage"] for s in found.get("stage_statuses", []) if isinstance(s, dict)}
    assert "dataset_regularization" in stage_names


def test_dp_project_run_requires_regularize_first(client: TestClient) -> None:
    project = create_dp_project(client)
    project_id = project["id"]
    upload_dataset_to_project(client, project_id)

    # Run before regularize should fail
    run_response = client.post(f"/api/analysis/projects/{project_id}/run")
    assert run_response.status_code in {400, 422}


def test_non_dp_project_upload_still_uses_retail_v2_path(client: TestClient) -> None:
    # Create a project WITHOUT analysis_kind (legacy Retail V2)
    response = client.post(
        "/api/analysis/projects",
        json={"name": "Legacy Retail Project", "description": "legacy"},
    )
    assert response.status_code == 201
    project = assert_success_payload(response.json())
    assert project.get("analysis_kind") is None
    project_id = project["id"]

    # Upload an incompatible CSV should trigger Retail V2 validation error
    fixture_path = Path("tests/fixtures/data_processing/mini_retail.csv")
    with fixture_path.open("rb") as dataset_file:
        upload_response = client.post(
            f"/api/analysis/projects/{project_id}/dataset",
            files={"file": (fixture_path.name, dataset_file, "text/csv")},
        )

    # Legacy Retail V2 path validates the 17 Chinese columns, so this must fail
    assert upload_response.status_code == 400
    error_payload = upload_response.json()
    assert "detail" in error_payload or "error" in error_payload
