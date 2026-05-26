"""Pipeline tests for data-processing chain."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.business.pipelines.dataset_regularization_pipeline import DatasetRegularizationPipeline
from backend.business.pipelines.universal_overview_pipeline import UniversalOverviewPipeline
from backend.providers.container import ProvidersContainer
from tests.fakes.providers import (
    FakeAnalysisArtifactProvider,
    FakeAnalysisJobProvider,
    FakeAnalysisModelStoreProvider,
    FakeAssociationRuleStoreProvider,
    FakeDatasetProvider,
    FakeGeneratedAssetProvider,
    FakeLLMProvider,
    FakeProjectFileStorageProvider,
    FakeProjectRepositoryProvider,
    FakeRecommendationModelStoreProvider,
    FakeRegularizedDatasetProvider,
    FakeRetailDatasetProvider,
    FakeSpeechSynthesisProvider,
    FakeTelemetryProvider,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "data_processing"


def _make_container(tmp_path: Path) -> ProvidersContainer:
    return ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        retail_dataset=FakeRetailDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        analysis_artifacts=FakeAnalysisArtifactProvider(),
        analysis_models=FakeAnalysisModelStoreProvider(),
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
        regularized_dataset=FakeRegularizedDatasetProvider(),
    )


class TestDatasetRegularizationPipeline:
    def test_runs_end_to_end(self, tmp_path: Path) -> None:
        container = _make_container(tmp_path)
        pipeline = DatasetRegularizationPipeline(container)
        content = (FIXTURES / "mini_retail.csv").read_bytes()
        result = pipeline.run("proj-1", "job-1", "mini_retail.csv", content)

        assert result.normalized_dataset_ref is not None
        assert result.mapping_ref is not None
        assert result.quality_ref is not None
        assert result.capability_ref is not None
        assert isinstance(result.quality, dict)
        assert isinstance(result.capability, dict)
        assert isinstance(result.mapping_detail, list)

    def test_generates_order_id_when_missing(self, tmp_path: Path) -> None:
        container = _make_container(tmp_path)
        pipeline = DatasetRegularizationPipeline(container)
        content = (FIXTURES / "missing_optional.csv").read_bytes()
        result = pipeline.run("proj-1", "job-2", "missing_optional.csv", content)

        assert result.needs_review is False or result.needs_review is True
        assert result.capability.get("can_run_sales_stats") is True


class TestUniversalOverviewPipeline:
    def test_runs_on_normalized_data(self, tmp_path: Path) -> None:
        container = _make_container(tmp_path)
        df = pd.DataFrame(
            {
                "user_id": ["U001", "U002"],
                "amount": [10.0, 20.0],
                "sale_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            }
        )
        pipeline = UniversalOverviewPipeline(container)
        result = pipeline.run("proj-1", "job-1", df, {})
        assert result is not None
