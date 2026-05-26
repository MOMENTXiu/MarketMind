"""Tests for text-only customer suggestion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.business.pipelines.customer_text_suggestion_pipeline import (
    CustomerTextSuggestionPipeline,
)
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
    FakeTelemetryProvider,
)


def _make_container(tmp_path: Path) -> tuple[ProvidersContainer, FakeLLMProvider]:
    llm = FakeLLMProvider(text="pipeline suggestion")
    container = ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        retail_dataset=FakeRetailDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        analysis_artifacts=FakeAnalysisArtifactProvider(),
        analysis_models=FakeAnalysisModelStoreProvider(),
        llm=llm,
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
        regularized_dataset=FakeRegularizedDatasetProvider(),
    )
    return container, llm


@pytest.mark.anyio
async def test_customer_text_suggestion_pipeline_returns_text_without_audio_url(
    tmp_path: Path,
) -> None:
    container, llm = _make_container(tmp_path)
    pipeline = CustomerTextSuggestionPipeline(container)

    result = await pipeline.generate(
        data={"customer_id": "C1", "cluster_name": "高价值客户"},
        llm_config={
            "provider": "openai",
            "baseUrl": "https://example.test",
            "apiKey": "redacted",
            "modelName": "demo-model",
        },
    )

    assert result["success"] is True
    assert result["text"] == "pipeline suggestion"
    assert "metadata" in result
    assert "audio_url" not in result
    assert len(llm.requests) == 1
