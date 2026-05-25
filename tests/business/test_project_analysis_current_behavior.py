"""Behavior anchors for the current project analysis lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.core.storage import ProjectStorage
from backend.models.project import Project, ProjectStatus
from backend.models.schemas import AssociationRule, AssociationRuleResponse
from backend.services import analysis_service


class FakeAssociationService:
    def __init__(self, data_path: str) -> None:
        self.data_path = data_path

    async def analyze(
        self,
        min_support: float,
        min_confidence: float,
        min_lift: float,
        top_n: int,
    ) -> AssociationRuleResponse:
        return AssociationRuleResponse(
            success=True,
            message="fake association ok",
            rules=[
                AssociationRule(
                    antecedents=["Milk"],
                    consequent="Bread",
                    support=0.2,
                    confidence=0.8,
                    lift=1.4,
                    strategy="bundle",
                )
            ],
        )


class FakePredictionService:
    def __init__(self, data_path: str) -> None:
        self.data_path = data_path

    async def analyze(self, forecast_weeks: int) -> dict:
        return {
            "success": True,
            "data": {
                "sales_r2": 0.91,
                "profit_r2": 0.82,
                "train_samples": 8,
                "forecast_weeks": forecast_weeks,
                "forecast_data": [
                    {"week": 1, "sales": 1200.0, "profit": 300.0},
                ],
            },
        }


class FakeClusteringService:
    def __init__(self, data_path: str) -> None:
        self.data_path = data_path

    async def analyze(self, n_clusters: int, save_path: str) -> dict:
        Path(save_path).write_text(
            "客户ID,R_最近购买天数,F_购买频次,M_消费金额,客户分群\nC001,5,2,100.0,0\n",
            encoding="utf-8",
        )
        return {
            "success": True,
            "data": {
                "n_clusters": n_clusters,
                "silhouette_score": 0.55,
                "total_customers": 1,
                "cluster_profiles": [
                    {
                        "cluster_name": "普通活跃客户",
                        "customer_count": 1,
                        "avg_recency": 5.0,
                        "avg_frequency": 2.0,
                        "avg_monetary": 100.0,
                        "avg_order_value": 50.0,
                        "marketing_strategy": "满减优惠券、交叉销售",
                    }
                ],
            },
        }


class FakeTTSService:
    async def synthesize(self, text: str, output_path: str) -> None:
        Path(output_path).write_bytes(b"fake report audio")


class FakeModelBuilderService:
    def __init__(self, data_path: str) -> None:
        self.data_path = data_path

    async def build_and_save(
        self,
        n_clusters: int,
        association_rules: list,
        output_path: str,
    ) -> dict:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake model")
        return {
            "success": True,
            "total_customers": 1,
            "n_clusters": n_clusters,
            "n_rules": len(association_rules),
        }


@pytest.fixture()
def isolated_analysis_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> ProjectStorage:
    storage = ProjectStorage(str(tmp_path / "data"))
    monkeypatch.setattr(analysis_service, "storage", storage)
    return storage


@pytest.fixture()
def fake_analysis_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> list[str]:
    cache_clear_calls: list[str] = []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(analysis_service, "AssociationService", FakeAssociationService)
    monkeypatch.setattr(analysis_service, "PredictionService", FakePredictionService)
    monkeypatch.setattr(analysis_service, "ClusteringService", FakeClusteringService)
    monkeypatch.setattr(analysis_service, "TTSService", FakeTTSService)
    monkeypatch.setattr(analysis_service, "ModelBuilderService", FakeModelBuilderService)
    monkeypatch.setattr(
        analysis_service,
        "clear_recommender_cache",
        lambda: cache_clear_calls.append("cleared"),
    )
    return cache_clear_calls


def create_project_with_dataset(storage: ProjectStorage, dataset_path: Path) -> Project:
    project = Project(
        name="Analysis Contract",
        dataset_filename="dataset.csv",
        dataset_path=str(dataset_path),
        status=ProjectStatus.PROCESSING,
    )
    return storage.create_project(project)


@pytest.mark.anyio
async def test_project_analysis_success_updates_outputs_and_cache(
    isolated_analysis_storage: ProjectStorage,
    fake_analysis_dependencies: list[str],
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.csv"
    dataset_path.write_text("订单日期,客户 ID,子类别,销售额,数量,折扣,利润\n", encoding="utf-8")
    project = create_project_with_dataset(isolated_analysis_storage, dataset_path)

    await analysis_service.run_project_analysis(project.id)

    updated_project = isolated_analysis_storage.get_project(project.id)
    assert updated_project is not None
    assert updated_project.status == ProjectStatus.COMPLETED
    assert updated_project.error_message is None
    assert updated_project.results is not None
    assert updated_project.results.association_rules is not None
    assert updated_project.results.association_rules[0]["consequent"] == "Bread"
    assert updated_project.results.prediction_data is not None
    assert updated_project.results.prediction_data["sales_r2"] == 0.91
    assert updated_project.results.clustering_data is not None
    assert updated_project.results.clustering_data["customers_csv"].endswith("customers.csv")

    report_path = Path(updated_project.results.report_path or "")
    audio_path = Path(updated_project.results.audio_path or "")
    customers_path = isolated_analysis_storage.get_project_dir(project.id) / "customers.csv"
    model_path = tmp_path / "backend/data/model_data.pkl"

    assert report_path.exists()
    assert f"# {project.name} - 营销分析报告" in report_path.read_text(encoding="utf-8")
    assert audio_path.exists()
    assert audio_path.read_bytes() == b"fake report audio"
    assert customers_path.exists()
    assert model_path.exists()
    assert fake_analysis_dependencies == ["cleared"]


@pytest.mark.anyio
async def test_project_analysis_failure_sets_failed_status_and_error_message(
    isolated_analysis_storage: ProjectStorage,
    fake_analysis_dependencies: list[str],
    tmp_path: Path,
) -> None:
    missing_dataset_path = tmp_path / "missing.csv"
    project = create_project_with_dataset(isolated_analysis_storage, missing_dataset_path)

    await analysis_service.run_project_analysis(project.id)

    updated_project = isolated_analysis_storage.get_project(project.id)
    assert updated_project is not None
    assert updated_project.status == ProjectStatus.FAILED
    assert updated_project.error_message is not None
    assert "分析失败: 数据集不存在" in updated_project.error_message
    assert fake_analysis_dependencies == []
