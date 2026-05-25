"""Pipeline contract tests for AIVoiceBroadcastPipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.business.pipelines.ai_voice_broadcast_pipeline import AIVoiceBroadcastPipeline
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


def _make_container(
    tmp_path: Path,
) -> tuple[ProvidersContainer, FakeGeneratedAssetProvider, FakeLLMProvider]:
    assets = FakeGeneratedAssetProvider(tmp_path / "assets")
    llm = FakeLLMProvider(text="broadcast text")
    return (
        ProvidersContainer(
            repository=FakeProjectRepositoryProvider(),
            storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
            assets=assets,
            dataset=FakeDatasetProvider(),
            association_rules=FakeAssociationRuleStoreProvider(),
            recommendation_models=FakeRecommendationModelStoreProvider(),
            speech=FakeSpeechSynthesisProvider(),
            llm=llm,
            analysis_jobs=FakeAnalysisJobProvider(),
            telemetry=FakeTelemetryProvider(),
        ),
        assets,
        llm,
    )


@pytest.mark.anyio
async def test_broadcast_returns_ai_audio_url(tmp_path: Path) -> None:
    container, assets, llm = _make_container(tmp_path)
    pipeline = AIVoiceBroadcastPipeline(container)
    result = await pipeline.broadcast(
        data={"customer_name": "Alice"},
        llm_config={
            "provider": "openai",
            "baseUrl": "https://example.com",
            "modelName": "gpt-test",
        },
        scene_type="clustering",
    )
    assert result["success"] is True
    assert result["text"] == "broadcast text"
    assert result["audio_url"].startswith("/api/ai-voice/audio/")
    assert len(llm.requests) == 1
    assert len(assets.ai_audio_calls) == 1
