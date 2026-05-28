"""Tests for MinioRegularizedDatasetAdapter with a fake object store."""

from __future__ import annotations

import pandas as pd
import pytest

from backend.infrastructure.adapters.minio_regularized_dataset_adapter import (
    MinioRegularizedDatasetAdapter,
)
from tests.infrastructure.adapters.test_minio_object_storage_adapter import (
    _FakeObjectStorage,
)


@pytest.fixture
def adapter() -> MinioRegularizedDatasetAdapter:
    return MinioRegularizedDatasetAdapter(_FakeObjectStorage())


class TestRawUpload:
    def test_save_raw_upload(self, adapter: MinioRegularizedDatasetAdapter) -> None:
        ref = adapter.save_raw_upload("proj-1", "job-1", "order.csv", b"a,b\n1,2\n")
        assert ref.project_id == "proj-1"
        assert ref.job_id == "job-1"
        assert ref.type == "raw_upload"
        assert ref.name == "order.csv"
        assert "uploads/" in ref.storage_key
        assert "upload_uuid" in ref.metadata

    def test_load_raw_upload(self, adapter: MinioRegularizedDatasetAdapter) -> None:
        ref = adapter.save_raw_upload("proj-1", "job-1", "order.csv", b"a,b\n1,2\n")
        data = adapter.load_raw_upload("proj-1", "job-1", ref)
        assert data == b"a,b\n1,2\n"


class TestNormalizedDataset:
    def test_save_and_load(self, adapter: MinioRegularizedDatasetAdapter) -> None:
        df = pd.DataFrame({"user_id": ["u1"], "item_id": ["i1"], "sale_date": ["2024-01-01"]})
        ref = adapter.save_normalized_dataset("proj-1", "job-1", df)
        assert ref.type == "normalized_dataset"
        assert ref.storage_key.startswith(
            "projects/proj-1/analysis/regularization/job-1/normalized/"
        )
        loaded = adapter.load_normalized_dataset("proj-1", "job-1", ref)
        assert isinstance(loaded, pd.DataFrame)
        assert list(loaded.columns) == ["user_id", "item_id", "sale_date"]


class TestSidecars:
    def test_save_and_load(self, adapter: MinioRegularizedDatasetAdapter) -> None:
        ref = adapter.save_sidecar("proj-1", "job-1", "quality", {"score": 0.9})
        assert ref.sidecar_type == "quality"
        assert ref.storage_key.endswith("/quality.json")
        loaded = adapter.load_sidecar("proj-1", "job-1", ref)
        assert loaded == {"score": 0.9}

    def test_list_sidecars(self, adapter: MinioRegularizedDatasetAdapter) -> None:
        adapter.save_sidecar("proj-1", "job-1", "quality", {"score": 0.9})
        adapter.save_sidecar("proj-1", "job-1", "capability", {"runnable": True})
        refs = adapter.list_sidecars("proj-1", "job-1")
        assert len(refs) == 2
        assert {r.sidecar_type for r in refs} == {"capability", "quality"}

    def test_resolve_sidecar_ref(self, adapter: MinioRegularizedDatasetAdapter) -> None:
        adapter.save_sidecar("proj-1", "job-1", "quality", {"score": 0.9})
        resolved = adapter.resolve_sidecar_ref("proj-1", "job-1", "sidecar:quality")
        assert resolved is not None
        assert resolved.sidecar_type == "quality"

    def test_resolve_missing_sidecar_returns_none(
        self, adapter: MinioRegularizedDatasetAdapter
    ) -> None:
        assert adapter.resolve_sidecar_ref("proj-1", "job-1", "sidecar:missing") is None


class TestRefResolution:
    def test_resolve_raw_upload(self, adapter: MinioRegularizedDatasetAdapter) -> None:
        adapter.save_raw_upload("proj-1", "job-1", "order.csv", b"data")
        resolved = adapter.resolve_dataset_ref("proj-1", "job-1", "raw-upload")
        assert resolved is not None
        assert resolved.type == "raw_upload"

    def test_resolve_normalized_dataset(self, adapter: MinioRegularizedDatasetAdapter) -> None:
        df = pd.DataFrame({"user_id": ["u1"]})
        adapter.save_normalized_dataset("proj-1", "job-1", df)
        resolved = adapter.resolve_dataset_ref("proj-1", "job-1", "normalized-dataset")
        assert resolved is not None
        assert resolved.type == "normalized_dataset"

    def test_resolve_unknown_ref_returns_none(
        self, adapter: MinioRegularizedDatasetAdapter
    ) -> None:
        assert adapter.resolve_dataset_ref("proj-1", "job-1", "unknown") is None
