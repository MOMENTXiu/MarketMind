"""Smoke tests for current public API contracts before architecture migration."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ai_voice as ai_voice_api
from backend.api import association as association_api
from backend.api import projects as projects_api
from backend.api import recommend as recommend_api
from backend.api import voice as voice_api
from backend.core.storage import ProjectStorage
from backend.main import app
from backend.models.schemas import AssociationRuleResponse


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def isolated_project_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStorage:
    storage = ProjectStorage(str(tmp_path / "data"))
    monkeypatch.setattr(projects_api, "storage", storage)
    return storage


def create_project(client: TestClient, name: str = "Contract Project") -> str:
    response = client.post(
        "/api/projects/",
        json={"name": name, "description": "contract smoke"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["id"]
    return payload["data"]["id"]


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


def test_project_crud_contracts(
    client: TestClient,
    isolated_project_storage: ProjectStorage,
) -> None:
    project_id = create_project(client)

    list_response = client.get("/api/projects/")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["success"] is True
    assert list_payload["total"] == 1
    assert list_payload["data"][0]["id"] == project_id

    get_response = client.get(f"/api/projects/{project_id}/")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["status"] == "待处理"

    update_response = client.put(
        f"/api/projects/{project_id}/",
        json={"name": "Updated Contract Project"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Updated Contract Project"

    missing_response = client.get("/api/projects/missing/")
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "项目不存在"

    delete_response = client.delete(f"/api/projects/{project_id}/")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"success": True, "message": "删除项目成功"}
    assert isolated_project_storage.get_project(project_id) is None


def test_upload_reanalyze_customers_and_project_recommend_contracts(
    client: TestClient,
    isolated_project_storage: ProjectStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = create_project(client)
    scheduled: list[str] = []

    def fake_run_project_analysis(project_id_arg: str) -> None:
        scheduled.append(project_id_arg)

    monkeypatch.setattr(projects_api, "run_project_analysis", fake_run_project_analysis)

    invalid_upload = client.post(
        f"/api/projects/{project_id}/upload/",
        files={"file": ("dataset.txt", b"not,csv", "text/plain")},
    )
    assert invalid_upload.status_code == 400
    assert invalid_upload.json()["detail"] == "仅支持 CSV 和 Excel 文件"

    valid_upload = client.post(
        f"/api/projects/{project_id}/upload/",
        files={"file": ("dataset.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert valid_upload.status_code == 200
    assert valid_upload.json() == {
        "success": True,
        "message": "文件上传成功，开始分析",
        "project_id": project_id,
    }
    project = isolated_project_storage.get_project(project_id)
    assert project is not None
    assert project.dataset_filename == "dataset.csv"
    assert project.status == "处理中"
    assert scheduled == [project_id]

    reanalyze_response = client.post(f"/api/projects/{project_id}/reanalyze/")
    assert reanalyze_response.status_code == 200
    assert reanalyze_response.json() == {
        "success": True,
        "message": "重新分析任务已启动",
    }
    assert scheduled == [project_id, project_id]

    customers_csv = isolated_project_storage.get_project_dir(project_id) / "customers.csv"
    customers_csv.write_text(
        "客户ID,R_最近购买天数,F_购买频次,M_消费金额,客户分群\nC001,7,3,188.5,2\n",
        encoding="utf-8",
    )
    customers_response = client.get(f"/api/projects/{project_id}/customers/?cluster_id=2")
    assert customers_response.status_code == 200
    assert customers_response.json() == {
        "success": True,
        "data": [
            {
                "id": "C001",
                "name": "C001",
                "recency": 7,
                "frequency": 3,
                "monetary": 188.5,
                "cluster_id": 2,
            }
        ],
    }

    monkeypatch.setattr(
        projects_api,
        "query_item_relations",
        lambda item, dataset_path=None: {
            "item": item,
            "dataset_path": dataset_path,
            "upstream": [],
            "downstream": [{"item": "Tea", "confidence": 0.5, "lift": 1.2}],
        },
    )
    recommend_response = client.get(f"/api/projects/{project_id}/recommend/?item=Milk")
    assert recommend_response.status_code == 200
    recommend_payload = recommend_response.json()
    assert recommend_payload["item"] == "Milk"
    assert recommend_payload["downstream"][0]["item"] == "Tea"
    assert recommend_payload["dataset_path"] == project.dataset_path


def test_reanalyze_missing_dataset_contract(
    client: TestClient,
    isolated_project_storage: ProjectStorage,
) -> None:
    project_id = create_project(client, name="No Dataset")

    response = client.post(f"/api/projects/{project_id}/reanalyze/")
    assert response.status_code == 400
    assert response.json()["detail"] == "项目未上传数据集"


class FakeRecommender:
    has_model = False
    subcategories = ["Milk"]

    def recommend_user(self, user_id: str) -> dict:
        return {
            "recommends": [{"item": "Milk", "reason": f"user:{user_id}"}],
            "cluster": {"cluster_name": "活跃客户", "strategy": "会员优惠"},
        }

    def recommend_item(self, item_name: str) -> dict:
        return {
            "upstream": [{"item": "Bread", "confidence": 0.4}],
            "downstream": [{"item": item_name, "confidence": 0.6}],
            "target_customers": [{"cluster_name": "高价值客户"}],
        }

    def calculate_realtime_rules(self, item_name: str, min_confidence: float) -> list[dict]:
        return [{"item": item_name, "confidence": min_confidence, "lift": 1.5}]


def test_recommendation_api_contracts(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recommend_api, "get_recommender", lambda: FakeRecommender())

    user_response = client.get("/api/recommend/user/?user_id=U001")
    assert user_response.status_code == 200
    user_payload = user_response.json()
    assert user_payload["item"] == "U001"
    assert user_payload["recommends"][0]["item"] == "Milk"
    assert user_payload["warning"] == "预训练模型未加载，使用热门商品推荐"

    item_response = client.get("/api/recommend/item/?item=Milk")
    assert item_response.status_code == 200
    item_payload = item_response.json()
    assert item_payload["success"] is True
    assert item_payload["downstream"][0]["item"] == "Milk"

    calculate_response = client.post(
        "/api/recommend/calculate/",
        json={"item": "Milk", "min_confidence": 0.25},
    )
    assert calculate_response.status_code == 200
    calculate_payload = calculate_response.json()
    assert calculate_payload["success"] is True
    assert calculate_payload["source"] == "realtime_calculation"
    assert calculate_payload["rules"][0]["confidence"] == 0.25

    missing_item_response = client.post("/api/recommend/calculate/", json={"item": "Unknown"})
    assert missing_item_response.status_code == 200
    assert missing_item_response.json() == {
        "success": False,
        "message": "商品不存在于数据集中",
        "rules": [],
    }


def test_association_and_voice_contracts(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_analyze(**kwargs: object) -> AssociationRuleResponse:
        return AssociationRuleResponse(success=True, message="ok", data={"kwargs": kwargs})

    monkeypatch.setattr(association_api.service, "analyze", fake_analyze)
    association_response = client.post("/api/association/analyze/", json={"top_n": 3})
    assert association_response.status_code == 200
    assert association_response.json()["success"] is True

    status_response = client.get("/api/association/status/")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "ready"

    async def fake_voice_synthesize(
        text: str,
        output_path: str,
        voice: str | None = None,
        rate: str | None = None,
        volume: str | None = None,
    ) -> None:
        Path(output_path).write_bytes(b"fake voice audio")

    monkeypatch.setattr(voice_api.tts_service, "synthesize", fake_voice_synthesize)
    monkeypatch.chdir(tmp_path)

    tts_response = client.post("/api/voice/tts/", json={"text": "hello"})
    assert tts_response.status_code == 200
    tts_payload = tts_response.json()
    assert tts_payload["success"] is True
    assert tts_payload["audio_url"].startswith("/outputs/audio/tts_")
    assert tts_payload["text"] == "hello"

    voice_response = client.post("/api/voice/generate/", json={"text": "custom voice"})
    assert voice_response.status_code == 200
    assert voice_response.json()["audio_url"] == "/outputs/audio/temp.mp3"


def test_ai_voice_contracts(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_broadcast(**kwargs: object) -> dict:
        return {
            "success": True,
            "text": "generated broadcast",
            "audio_path": "/tmp/contract-broadcast.mp3",
        }

    async def fake_tts(
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        volume: str | None = None,
    ) -> str:
        return "/tmp/contract-tts.mp3"

    monkeypatch.setattr(ai_voice_api.AIVoiceService, "generate_voice_broadcast", fake_broadcast)
    monkeypatch.setattr(ai_voice_api.AIVoiceService, "text_to_speech", fake_tts)

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
