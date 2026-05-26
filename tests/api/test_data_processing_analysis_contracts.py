"""Data Processing Analysis API contract tests."""

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


def assert_ref_is_path_free(ref: dict[str, Any]) -> None:
    assert "path" not in ref
    assert not any(marker in str(ref) for marker in LOCAL_ARTIFACT_MARKERS)


def create_job(client: TestClient, project_id: str = "test-project") -> str:
    response = client.post(
        "/api/analysis/jobs",
        json={"project_id": project_id, "name": "Data Processing Contract"},
    )
    assert response.status_code == 201
    data = assert_success_payload(response.json())
    assert data["project_id"] == project_id
    assert data["name"] == "Data Processing Contract"
    assert data["status"] == "queued"
    assert isinstance(data["job_id"], str) and data["job_id"]
    assert isinstance(data["stages"], list)
    assert {stage["stage"] for stage in data["stages"]} == REQUIRED_STAGE_NAMES
    for stage in data["stages"]:
        assert_stage_contract(stage)
    return data["job_id"]


def upload_raw_dataset(client: TestClient, project_id: str, job_id: str) -> dict[str, Any]:
    fixture_path = Path("tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv")
    with fixture_path.open("rb") as dataset_file:
        response = client.post(
            f"/api/analysis/jobs/{job_id}/raw-dataset?project_id={project_id}",
            files={"file": (fixture_path.name, dataset_file, "text/csv")},
        )
    assert response.status_code == 200
    data = assert_success_payload(response.json())
    assert data["project_id"] == project_id
    assert data["job_id"] == job_id
    assert data["status"] == "queued"
    assert isinstance(data["output_refs"], list)
    return data


def test_create_data_processing_job_contract(client: TestClient) -> None:
    job_id = create_job(client)
    get_response = client.get(f"/api/analysis/jobs/{job_id}?project_id=test-project")
    assert get_response.status_code == 200
    data = assert_success_payload(get_response.json())
    assert data["job_id"] == job_id


def test_upload_raw_dataset_contract(client: TestClient) -> None:
    job_id = create_job(client)
    upload_raw_dataset(client, "test-project", job_id)


def test_regularize_dataset_contract(client: TestClient) -> None:
    job_id = create_job(client)
    upload_raw_dataset(client, "test-project", job_id)

    response = client.post(f"/api/analysis/jobs/{job_id}/regularize?project_id=test-project")
    assert response.status_code == 200

    data = assert_success_payload(response.json())
    assert data["job_id"] == job_id
    assert data["status"] in VALID_JOB_STATUSES
    assert isinstance(data["quality"], dict)
    assert isinstance(data["capability"], dict)
    assert isinstance(data["output_refs"], list)
    for ref in data["output_refs"]:
        assert_ref_is_path_free(ref)
    for stage in data["stages"]:
        assert_stage_contract(stage)
    reg_stage = next(s for s in data["stages"] if s["stage"] == "dataset_regularization")
    assert reg_stage["status"] in {"completed", "needs_review"}


def test_run_analysis_contract(client: TestClient) -> None:
    job_id = create_job(client)
    upload_raw_dataset(client, "test-project", job_id)

    reg_response = client.post(f"/api/analysis/jobs/{job_id}/regularize?project_id=test-project")
    assert reg_response.status_code == 200
    reg_data = assert_success_payload(reg_response.json())

    run_response = client.post(f"/api/analysis/jobs/{job_id}/run?project_id=test-project")
    if reg_data["status"] == "needs_review":
        assert run_response.status_code in {400, 422}
        assert_error_payload(run_response.json())
    else:
        assert run_response.status_code in {200, 202}
        data = assert_success_payload(run_response.json())
        assert data["job_id"] == job_id
        assert data["status"] in VALID_JOB_STATUSES


def test_list_outputs_contract(client: TestClient) -> None:
    job_id = create_job(client)
    upload_raw_dataset(client, "test-project", job_id)

    response = client.get(f"/api/analysis/jobs/{job_id}/outputs?project_id=test-project")
    assert response.status_code == 200

    data = assert_success_payload(response.json())
    assert data["project_id"] == "test-project"
    assert data["job_id"] == job_id
    assert isinstance(data["outputs"], list)


def test_run_before_upload_fails(client: TestClient) -> None:
    job_id = create_job(client)
    response = client.post(f"/api/analysis/jobs/{job_id}/run?project_id=test-project")
    assert response.status_code in {400, 422}
    assert_error_payload(response.json())


def test_run_before_regularize_fails(client: TestClient) -> None:
    job_id = create_job(client)
    upload_raw_dataset(client, "test-project", job_id)
    response = client.post(f"/api/analysis/jobs/{job_id}/run?project_id=test-project")
    assert response.status_code in {400, 422}
    assert_error_payload(response.json())


def test_dataset_and_sidecar_url_contracts(isolated_env_real_adapter: Any) -> None:
    client = TestClient(app)
    job_id = create_job(client)
    upload_raw_dataset(client, "test-project", job_id)

    reg_response = client.post(f"/api/analysis/jobs/{job_id}/regularize?project_id=test-project")
    assert reg_response.status_code == 200
    reg_data = assert_success_payload(reg_response.json())

    refs = {ref["id"]: ref for ref in reg_data.get("output_refs", [])}
    assert "raw-upload" in refs
    assert "normalized-dataset" in refs

    ds_response = client.get(
        f"/api/analysis/jobs/{job_id}/datasets/raw-upload?project_id=test-project"
    )
    assert ds_response.status_code == 200
    ds_data = assert_success_payload(ds_response.json())
    assert ds_data["id"] == "raw-upload"
    assert ds_data["type"] == "raw_upload"

    norm_response = client.get(
        f"/api/analysis/jobs/{job_id}/datasets/normalized-dataset?project_id=test-project"
    )
    assert norm_response.status_code == 200
    norm_data = assert_success_payload(norm_response.json())
    assert norm_data["id"] == "normalized-dataset"
    assert norm_data["type"] == "normalized_dataset"

    cap_response = client.get(
        f"/api/analysis/jobs/{job_id}/sidecars/sidecar:capability?project_id=test-project"
    )
    assert cap_response.status_code == 200
    cap_data = assert_success_payload(cap_response.json())
    assert isinstance(cap_data, dict)

    missing_ds = client.get(f"/api/analysis/jobs/{job_id}/datasets/unknown?project_id=test-project")
    assert missing_ds.status_code == 404

    missing_sc = client.get(
        f"/api/analysis/jobs/{job_id}/sidecars/sidecar:missing?project_id=test-project"
    )
    assert missing_sc.status_code == 404


def test_run_analysis_with_real_adapter(isolated_env_real_adapter: Any) -> None:
    client = TestClient(app)
    job_id = create_job(client)
    upload_raw_dataset(client, "test-project", job_id)

    reg_response = client.post(f"/api/analysis/jobs/{job_id}/regularize?project_id=test-project")
    assert reg_response.status_code == 200
    reg_data = assert_success_payload(reg_response.json())
    if reg_data["status"] != "completed":
        pytest.skip("Regularization did not complete; cannot test run with real adapter")

    run_response = client.post(f"/api/analysis/jobs/{job_id}/run?project_id=test-project")
    assert run_response.status_code in {200, 202}
    run_data = assert_success_payload(run_response.json())
    assert run_data["job_id"] == job_id
    assert run_data["status"] in VALID_JOB_STATUSES


def test_error_contracts(client: TestClient) -> None:
    invalid_create = client.post("/api/analysis/jobs", json={"project_id": "", "name": ""})
    assert invalid_create.status_code in {400, 422}
    assert_error_payload(invalid_create.json())

    missing_job = client.get("/api/analysis/jobs/missing-job?project_id=test")
    assert missing_job.status_code == 404
    assert_error_payload(missing_job.json())

    wrong_file = client.post(
        "/api/analysis/jobs/job-id/raw-dataset?project_id=test",
        files={"file": ("dataset.txt", b"not,a,csv", "text/plain")},
    )
    assert wrong_file.status_code in {400, 422}
    assert_error_payload(wrong_file.json())
