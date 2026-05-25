"""Contract tests for the local recommendation model store adapter."""

from __future__ import annotations

from backend.infrastructure.adapters.local_recommendation_model_store_adapter import (
    LocalRecommendationModelStoreAdapter,
)


def test_recommendation_model_store_load_save_and_missing_behavior(tmp_path) -> None:
    model_path = tmp_path / "backend/data/model_data.pkl"
    adapter = LocalRecommendationModelStoreAdapter(str(model_path))

    assert adapter.load_model() is None

    payload = {"model": "fake", "rules": [1, 2, 3]}
    saved = adapter.save_model(payload)

    assert saved.path == model_path
    assert saved.payload == payload
    loaded = adapter.load_model()
    assert loaded is not None
    assert loaded.path == model_path
    assert loaded.payload == payload


def test_recommendation_model_store_clear_cache_uses_injected_hook(tmp_path) -> None:
    calls: list[str] = []
    adapter = LocalRecommendationModelStoreAdapter(
        str(tmp_path / "model.pkl"),
        cache_clearer=lambda: calls.append("cleared"),
    )

    adapter.clear_cache()

    assert calls == ["cleared"]
