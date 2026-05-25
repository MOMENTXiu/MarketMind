"""Pipeline contract tests for ProjectCustomerPipeline and ProjectRecommendationPipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.business.pipelines.project_read_pipelines import (
    ProjectCustomerPipeline,
    ProjectRecommendationPipeline,
)
from backend.core.errors import NotFoundError
from backend.models.project import ProjectCreate
from backend.providers.container import ProvidersContainer
from tests.fakes.providers import (
    FakeAnalysisJobProvider,
    FakeAssociationRuleStoreProvider,
    FakeDatasetProvider,
    FakeGeneratedAssetProvider,
    FakeLLMProvider,
    FakeProjectFileStorageProvider,
    FakeProjectRepositoryProvider,
    FakeRecommendationModelStoreProvider,
    FakeSpeechSynthesisProvider,
    FakeTelemetryProvider,
)


def _basket_rules() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "antecedents": frozenset(["A"]),
                "consequents": frozenset(["B"]),
                "support": 0.5,
                "confidence": 0.8,
                "lift": 1.6,
                "strategy": "bundle",
            }
        ]
    )


def _make_container(
    tmp_path: Path,
    rules: pd.DataFrame | None = None,
) -> ProvidersContainer:
    return ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(rules=rules),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
    )


def test_customer_list_returns_normalized_rows(tmp_path: Path) -> None:
    container = _make_container(tmp_path)
    project = container.repository.create_project(ProjectCreate(name="demo"))
    pipeline = ProjectCustomerPipeline(container)
    rows = pipeline.list(project.id)
    assert isinstance(rows, list)
    assert rows[0]["id"] == "fake-customer"


def test_customer_list_missing_project_raises_not_found(tmp_path: Path) -> None:
    pipeline = ProjectCustomerPipeline(_make_container(tmp_path))
    with pytest.raises(NotFoundError):
        pipeline.list("missing")


def test_project_recommendation_returns_item_payload(tmp_path: Path) -> None:
    container = _make_container(tmp_path, rules=_basket_rules())
    project = container.repository.create_project(ProjectCreate(name="demo"))
    dataset_path = container.storage.get_project_dir(project.id) / "dataset.csv"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text("col\n1\n", encoding="utf-8")
    pipeline = ProjectRecommendationPipeline(container)
    result = pipeline.recommend_for_item(project.id, item="A")
    assert result["item"] == "A"


def test_project_recommendation_missing_project_raises_not_found(tmp_path: Path) -> None:
    pipeline = ProjectRecommendationPipeline(_make_container(tmp_path))
    with pytest.raises(NotFoundError):
        pipeline.recommend_for_item("missing", item="A")


def test_project_recommendation_missing_dataset_raises_not_found(tmp_path: Path) -> None:
    container = _make_container(tmp_path)
    project = container.repository.create_project(ProjectCreate(name="demo"))
    pipeline = ProjectRecommendationPipeline(container)
    with pytest.raises(NotFoundError):
        pipeline.recommend_for_item(project.id, item="A")
