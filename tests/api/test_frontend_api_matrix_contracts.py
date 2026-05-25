"""Frontend-dependent API response shape contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ai_voice as ai_voice_api
from backend.api import projects as projects_api
from backend.api import recommend as recommend_api
from backend.api import voice as voice_api
from backend.core.storage import ProjectStorage
from backend.main import app
from backend.models.project import AnalysisResults, Project, ProjectStatus


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def isolated_project_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStorage:
    storage = ProjectStorage(str(tmp_path / "data"))
    monkeypatch.setattr(projects_api, "storage", storage)
    return storage


def test_project_create_list_detail_fields_used_by_frontend(
    client: TestClient,
    isolated_project_storage: ProjectStorage,
) -> None:
    create_response = client.post(
        "/api/projects/",
        json={"name": "Frontend Matrix", "parameters": {"min_support": 0.05}},
    )
    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["success"] is True
    assert create_payload["data"]["id"]

    project_id = create_payload["data"]["id"]
    isolated_project_storage.update_project(
        project_id,
        {
            "status": ProjectStatus.COMPLETED,
            "results": AnalysisResults(
                association_rules=[],
                prediction_data={"sales_r2": 0.9},
                clustering_data={"cluster_profiles": []},
                charts={"sales": "/outputs/charts/sales.png"},
                audio_path="/tmp/audio.mp3",
                report_path="/tmp/report.md",
            ).model_dump(),
        },
    )

    list_response = client.get("/api/projects/")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["success"] is True
    assert isinstance(list_payload["data"], list)
    assert {"id", "name", "status", "created_at", "updated_at"}.issubset(list_payload["data"][0])

    detail_response = client.get(f"/api/projects/{project_id}/")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()["data"]
    assert detail_data["status"] == "已完成"
    assert {"association_rules", "prediction_data", "clustering_data", "charts"}.issubset(
        detail_data["results"]
    )


def test_frontend_error_detail_and_customer_fields(
    client: TestClient,
    isolated_project_storage: ProjectStorage,
) -> None:
    missing_response = client.get("/api/projects/missing/")
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "项目不存在"}

    project = isolated_project_storage.create_project(
        Project(name="Customer Matrix", status=ProjectStatus.COMPLETED)
    )
    customers_csv = isolated_project_storage.get_project_dir(project.id) / "customers.csv"
    customers_csv.write_text(
        "客户ID,R_最近购买天数,F_购买频次,M_消费金额,客户分群\nC002,3,9,450.75,1\n",
        encoding="utf-8",
    )

    response = client.get(f"/api/projects/{project.id}/customers/")
    assert response.status_code == 200
    customer = response.json()["data"][0]
    assert {"id", "name", "recency", "frequency", "monetary", "cluster_id"}.issubset(customer)


class MatrixRecommender:
    has_model = True
    subcategories = ["Milk"]

    def recommend_user(self, user_id: str) -> dict:
        return {
            "recommends": [{"item": "Milk", "score": 0.8}],
            "cluster": {"cluster_name": "高价值客户", "strategy": "VIP专属优惠"},
        }

    def recommend_item(self, item_name: str) -> dict:
        return {
            "upstream": [{"item": "Bread", "confidence": 0.4, "lift": 1.1}],
            "downstream": [{"item": item_name, "confidence": 0.7, "lift": 1.6}],
            "target_customers": [{"cluster_name": "普通活跃客户"}],
        }

    def calculate_realtime_rules(self, item_name: str, min_confidence: float) -> list[dict]:
        return [{"item": item_name, "confidence": min_confidence, "lift": 1.3}]


def test_recommendation_fields_used_by_frontend(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recommend_api, "get_recommender", lambda: MatrixRecommender())

    item_response = client.get("/api/recommend/item/?item=Milk")
    assert item_response.status_code == 200
    item_payload = item_response.json()
    assert {"item", "upstream", "downstream", "target_customers", "success"}.issubset(item_payload)
    assert {"item", "confidence", "lift"}.issubset(item_payload["downstream"][0])

    user_response = client.get("/api/recommend/user/?user_id=C002")
    assert user_response.status_code == 200
    user_payload = user_response.json()
    assert {
        "item",
        "recommends",
        "target_customers",
        "speech",
        "model_tries",
        "human_fallback",
        "warning",
    }.issubset(user_payload)

    calculate_response = client.post("/api/recommend/calculate/", json={"item": "Milk"})
    assert calculate_response.status_code == 200
    calculate_payload = calculate_response.json()
    assert {"success", "item", "rules", "source"}.issubset(calculate_payload)
    assert calculate_payload["rules"]


def test_voice_and_ai_voice_fields_used_by_frontend(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_voice_synthesize(
        text: str,
        output_path: str,
        voice: str | None = None,
        rate: str | None = None,
        volume: str | None = None,
    ) -> None:
        Path(output_path).write_bytes(b"fake voice")

    async def fake_broadcast(**kwargs: object) -> dict:
        return {
            "success": True,
            "text": "front-end broadcast",
            "audio_path": "/tmp/frontend-broadcast.mp3",
        }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(voice_api.tts_service, "synthesize", fake_voice_synthesize)
    monkeypatch.setattr(ai_voice_api.AIVoiceService, "generate_voice_broadcast", fake_broadcast)

    voice_response = client.post("/api/voice/tts/", json={"text": "play this"})
    assert voice_response.status_code == 200
    assert {"success", "audio_url", "text"}.issubset(voice_response.json())
    assert voice_response.json()["audio_url"].startswith("/outputs/audio/")

    ai_response = client.post(
        "/api/ai-voice/broadcast/",
        json={
            "data": {"customer_id": "C002"},
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
    assert ai_response.status_code == 200
    assert ai_response.json() == {
        "success": True,
        "text": "front-end broadcast",
        "audio_url": "/api/ai-voice/audio/frontend-broadcast.mp3/",
    }
