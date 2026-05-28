"""Contract tests for sample file API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_list_samples() -> None:
    response = client.get("/api/samples")
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert isinstance(data["samples"], list)
    assert data["backend"] == "local"


def test_get_sample() -> None:
    response = client.get("/api/samples/order-sample")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "order-sample"
    assert "download_url" in data


def test_get_missing_sample() -> None:
    response = client.get("/api/samples/missing")
    assert response.status_code == 404


def test_download_sample_local_not_implemented() -> None:
    response = client.get("/api/samples/order-sample/download")
    assert response.status_code == 501
