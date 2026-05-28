"""Tests for MinioAnalysisModelStoreAdapter with a fake object store."""

from __future__ import annotations

import pytest

from backend.infrastructure.adapters.minio_analysis_model_store_adapter import (
    MinioAnalysisModelStoreAdapter,
)
from tests.infrastructure.adapters.test_minio_object_storage_adapter import (
    _FakeObjectStorage,
)


@pytest.fixture
def adapter() -> MinioAnalysisModelStoreAdapter:
    return MinioAnalysisModelStoreAdapter(_FakeObjectStorage())


class TestModelStore:
    def test_save_and_load(self, adapter: MinioAnalysisModelStoreAdapter) -> None:
        ref = adapter.save_model("proj-1", "segmentation", {"clusters": 4})
        assert ref.model_type == "segmentation"
        assert ref.version == "current"
        loaded = adapter.load_model("proj-1", "segmentation")
        assert loaded == {"clusters": 4}

    def test_resolve_model(self, adapter: MinioAnalysisModelStoreAdapter) -> None:
        adapter.save_model("proj-1", "segmentation", {"clusters": 4})
        resolved = adapter.resolve_model("proj-1", "segmentation")
        assert resolved is not None
        assert resolved.model_type == "segmentation"

    def test_list_models(self, adapter: MinioAnalysisModelStoreAdapter) -> None:
        adapter.save_model("proj-1", "segmentation", {"clusters": 4}, version="v1")
        adapter.save_model("proj-1", "recommendation", {"items": []}, version="v1")
        refs = adapter.list_models("proj-1")
        assert len(refs) == 2
        types = {r.model_type for r in refs}
        assert types == {"recommendation", "segmentation"}

    def test_delete_model(self, adapter: MinioAnalysisModelStoreAdapter) -> None:
        adapter.save_model("proj-1", "segmentation", {"clusters": 4})
        assert adapter.delete_model("proj-1", "segmentation")
        assert not adapter.delete_model("proj-1", "segmentation")
        assert adapter.resolve_model("proj-1", "segmentation") is None

    def test_load_missing_returns_none(self, adapter: MinioAnalysisModelStoreAdapter) -> None:
        assert adapter.load_model("proj-1", "missing") is None
