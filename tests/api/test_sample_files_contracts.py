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


def test_download_sample_local() -> None:
    response = client.get("/api/samples/order-sample/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]


def test_download_order_sample_2() -> None:
    response = client.get("/api/samples/order-sample-2")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "order-sample-2"
    assert "download_url" in data

    dl = client.get("/api/samples/order-sample-2/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in dl.headers["content-disposition"]
