"""Contract tests for sample file API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_list_samples() -> None:
    response = client.get("/api/samples")
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert isinstance(data["samples"], list)
    assert data["backend"] in ("local", "minio")


def test_get_sample() -> None:
    response = client.get("/api/samples/order-sample")
    if response.status_code == 404:
        pytest.skip("sample not available in current storage backend")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "download_url" in data


def test_get_missing_sample() -> None:
    response = client.get("/api/samples/missing")
    assert response.status_code == 404


def test_download_sample_local() -> None:
    # Resolve sample id via list first (backend may be local or minio)
    list_resp = client.get("/api/samples")
    samples = list_resp.json()["samples"]
    if not samples:
        pytest.skip("no samples available in current storage backend")
    sample_id = samples[0]["id"]
    response = client.get(f"/api/samples/{sample_id}/download")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


def test_download_order_sample_2() -> None:
    list_resp = client.get("/api/samples")
    samples = list_resp.json()["samples"]
    if len(samples) < 2:
        pytest.skip("fewer than 2 samples available in current storage backend")
    sample_id = samples[1]["id"]
    response = client.get(f"/api/samples/{sample_id}")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "download_url" in data

    dl = client.get(f"/api/samples/{sample_id}/download")
    assert dl.status_code == 200
    assert "text/csv" in dl.headers["content-type"]
    assert "attachment" in dl.headers["content-disposition"]
