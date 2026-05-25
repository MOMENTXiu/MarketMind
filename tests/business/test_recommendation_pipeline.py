"""Pipeline contract tests for RecommendationPipeline (global)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.business.pipelines.recommendation_pipeline import RecommendationPipeline
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


def _make_dataset() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for i in range(20):
        rows.append(
            {
                "订单 ID": f"O{i}",
                "客户 ID": f"C{i % 4}",
                "订单日期": "2024-01-01",
                "子类别": "A" if i % 2 == 0 else "B",
                "类别": "X",
                "销售额": 100.0 + i,
                "数量": 1,
                "折扣": 0.1,
                "利润": 10.0,
            }
        )
    return pd.DataFrame(rows)


def _make_container(
    tmp_path: Path,
) -> tuple[
    ProvidersContainer,
    FakeRecommendationModelStoreProvider,
    FakeAssociationRuleStoreProvider,
    FakeSpeechSynthesisProvider,
    FakeGeneratedAssetProvider,
]:
    models = FakeRecommendationModelStoreProvider()
    rules = FakeAssociationRuleStoreProvider()
    speech = FakeSpeechSynthesisProvider()
    assets = FakeGeneratedAssetProvider(tmp_path / "assets")
    container = ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=assets,
        dataset=FakeDatasetProvider(default_dataset=_make_dataset()),
        association_rules=rules,
        recommendation_models=models,
        speech=speech,
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
    )
    return container, models, rules, speech, assets


def test_recommend_user_without_model_returns_warning(tmp_path: Path) -> None:
    container, _models, _rules, _speech, _assets = _make_container(tmp_path)
    pipeline = RecommendationPipeline(container)
    result = pipeline.recommend_user(user_id="anyone", top_n=3)
    assert result["item"] == "anyone"
    assert isinstance(result["recommends"], list)
    assert "warning" in result


def test_recommend_item_returns_dict(tmp_path: Path) -> None:
    container, _models, _rules, _speech, _assets = _make_container(tmp_path)
    pipeline = RecommendationPipeline(container)
    result = pipeline.recommend_item(item="A", top_n=3)
    assert result["success"] is True
    assert result["item"] == "A"


def test_calculate_rules_missing_item_returns_failure(tmp_path: Path) -> None:
    container, _models, _rules, _speech, _assets = _make_container(tmp_path)
    pipeline = RecommendationPipeline(container)
    result = pipeline.calculate_rules(item="ZZZ", min_confidence=0.1)
    assert result["success"] is False
    assert result["rules"] == []


@pytest.mark.anyio
async def test_play_tts_publishes_audio(tmp_path: Path) -> None:
    container, _models, _rules, speech, assets = _make_container(tmp_path)
    pipeline = RecommendationPipeline(container)
    result = await pipeline.play_tts(project_id="proj-1", speech="hello")
    assert result["audio_url"].startswith("/outputs/audio/")
    assert len(speech.requests) == 1
    assert len(assets.public_audio_calls) == 1


def test_clear_model_cache_delegates(tmp_path: Path) -> None:
    container, models, _rules, _speech, _assets = _make_container(tmp_path)
    pipeline = RecommendationPipeline(container)
    pipeline.clear_model_cache()
    assert models.cache_cleared is True
