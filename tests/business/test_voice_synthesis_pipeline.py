"""Pipeline contract tests for VoiceSynthesisPipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.business.pipelines.voice_synthesis_pipeline import VoiceSynthesisPipeline
from backend.core.errors import ValidationError
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
) -> tuple[ProvidersContainer, FakeSpeechSynthesisProvider, FakeGeneratedAssetProvider]:
    speech = FakeSpeechSynthesisProvider()
    assets = FakeGeneratedAssetProvider(tmp_path / "assets")
    return (
        ProvidersContainer(
            repository=FakeProjectRepositoryProvider(),
            storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
            assets=assets,
            dataset=FakeDatasetProvider(),
            association_rules=FakeAssociationRuleStoreProvider(),
            recommendation_models=FakeRecommendationModelStoreProvider(),
            speech=speech,
            llm=FakeLLMProvider(),
            analysis_jobs=FakeAnalysisJobProvider(),
            telemetry=FakeTelemetryProvider(),
        ),
        speech,
        assets,
    )


@pytest.mark.anyio
async def test_synthesize_returns_public_audio_url(tmp_path: Path) -> None:
    container, speech, assets = _make_container(tmp_path)
    pipeline = VoiceSynthesisPipeline(container)
    result = await pipeline.synthesize(text="hello world")
    assert result["success"] is True
    assert result["audio_url"].startswith("/outputs/audio/")
    assert result["text"] == "hello world"
    assert len(speech.requests) == 1
    assert len(assets.public_audio_calls) == 1


@pytest.mark.anyio
async def test_synthesize_rejects_empty_text(tmp_path: Path) -> None:
    container, _, _ = _make_container(tmp_path)
    pipeline = VoiceSynthesisPipeline(container)
    with pytest.raises(ValidationError):
        await pipeline.synthesize(text="  ")
