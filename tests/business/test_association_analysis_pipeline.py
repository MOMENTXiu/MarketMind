"""Pipeline contract tests for AssociationAnalysisPipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.business.pipelines.association_analysis_pipeline import (
    AssociationAnalysisPipeline,
)
from backend.models.schemas import AssociationRuleRequest
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


def _basket_dataset() -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for order in range(1, 21):
        rows.append({"订单 ID": f"O{order}", "子类别": "A"})
        rows.append({"订单 ID": f"O{order}", "子类别": "B"})
    for order in range(1, 6):
        rows.append({"订单 ID": f"O{order}", "子类别": "C"})
    return pd.DataFrame(rows)


def _make_container(tmp_path: Path, dataset: pd.DataFrame | None) -> ProvidersContainer:
    return ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(default_dataset=dataset),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
    )


def test_analyze_returns_response_with_rules(tmp_path: Path) -> None:
    pipeline = AssociationAnalysisPipeline(_make_container(tmp_path, _basket_dataset()))
    response = pipeline.analyze(
        AssociationRuleRequest(min_support=0.05, min_confidence=0.1, min_lift=0.5, top_n=5)
    )
    assert response.success is True


def test_analyze_without_default_dataset_raises(tmp_path: Path) -> None:
    pipeline = AssociationAnalysisPipeline(_make_container(tmp_path, None))
    with pytest.raises(FileNotFoundError):
        pipeline.analyze(AssociationRuleRequest())
