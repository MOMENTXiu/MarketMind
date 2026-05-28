"""Tests for MinioAnalysisArtifactAdapter with a fake object store."""

from __future__ import annotations

import pytest

from backend.infrastructure.adapters.minio_analysis_artifact_adapter import (
    MinioAnalysisArtifactAdapter,
)
from tests.infrastructure.adapters.test_minio_object_storage_adapter import (
    _FakeObjectStorage,
)


@pytest.fixture
def adapter() -> MinioAnalysisArtifactAdapter:
    return MinioAnalysisArtifactAdapter(_FakeObjectStorage())


class TestArtifactSaveAndResolve:
    def test_save_json(self, adapter: MinioAnalysisArtifactAdapter) -> None:
        ref = adapter.save_json("proj-1", "summary", {"ready": True})
        assert ref.type == "json"
        assert ref.storage_key.startswith("projects/proj-1/analysis/artifacts/json/")
        resolved = adapter.resolve_artifact("proj-1", ref.id)
        assert resolved is not None
        assert resolved.id == ref.id

    def test_save_table(self, adapter: MinioAnalysisArtifactAdapter) -> None:
        ref = adapter.save_table("proj-1", "report", [{"a": 1}])
        assert ref.type == "table"
        payload = adapter.load_payload("proj-1", ref.id)
        assert payload is not None
        assert payload.payload_type == "table"
        assert payload.rows == [{"a": 1}]

    def test_save_markdown(self, adapter: MinioAnalysisArtifactAdapter) -> None:
        ref = adapter.save_markdown("proj-1", "report", "# Hello")
        payload = adapter.load_payload("proj-1", ref.id)
        assert payload is not None
        assert payload.content == "# Hello"

    def test_save_figure(self, adapter: MinioAnalysisArtifactAdapter) -> None:
        ref = adapter.save_figure("proj-1", "chart", b"\x89PNG", media_type="image/png")
        assert ref.type == "figure"
        assert ref.metadata["media_type"] == "image/png"

    def test_url_is_opaque(self, adapter: MinioAnalysisArtifactAdapter) -> None:
        ref = adapter.save_json("proj-1", "summary", {"ready": True})
        assert ref.url.startswith("/api/analysis/projects/proj-1/artifacts/")
        assert "/Users/" not in ref.url
        assert "data/projects" not in ref.url
        assert "json:summary" in ref.url

    def test_resolve_missing_returns_none(self, adapter: MinioAnalysisArtifactAdapter) -> None:
        assert adapter.resolve_artifact("proj-1", "json:missing.json") is None
