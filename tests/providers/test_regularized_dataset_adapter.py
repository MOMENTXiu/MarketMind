"""Adapter tests for LocalRegularizedDatasetAdapter."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.infrastructure.adapters.local_regularized_dataset_adapter import (
    LocalRegularizedDatasetAdapter,
)
from backend.providers.dtos import (
    RegularizationSidecarReferenceDTO,
    RegularizedDatasetReferenceDTO,
)


@pytest.fixture()
def adapter(tmp_path: Path) -> LocalRegularizedDatasetAdapter:
    return LocalRegularizedDatasetAdapter(str(tmp_path))


class TestSaveAndLoadRawUpload:
    def test_roundtrip(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        ref = adapter.save_raw_upload("proj-1", "job-1", "data.csv", b"a,b\n1,2\n")
        assert isinstance(ref, RegularizedDatasetReferenceDTO)
        assert ref.type == "raw_upload"
        assert ref.id == "raw-upload"
        assert "?project_id=proj-1" in ref.url

        loaded = adapter.load_raw_upload("proj-1", "job-1", ref)
        assert loaded == b"a,b\n1,2\n"


class TestSaveAndLoadNormalizedDataset:
    def test_roundtrip(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        ref = adapter.save_normalized_dataset("proj-1", "job-1", df)
        assert isinstance(ref, RegularizedDatasetReferenceDTO)
        assert ref.type == "normalized_dataset"
        assert ref.id == "normalized-dataset"
        assert "?project_id=proj-1" in ref.url

        loaded = adapter.load_normalized_dataset("proj-1", "job-1", ref)
        assert isinstance(loaded, pd.DataFrame)
        assert list(loaded.columns) == ["x", "y"]
        assert len(loaded) == 2


class TestSaveAndLoadSidecar:
    def test_dict_roundtrip(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        ref = adapter.save_sidecar("proj-1", "job-1", "quality", {"score": 0.9})
        assert isinstance(ref, RegularizationSidecarReferenceDTO)
        assert ref.sidecar_type == "quality"
        assert ref.id == "sidecar:quality"
        assert "?project_id=proj-1" in ref.url

        loaded = adapter.load_sidecar("proj-1", "job-1", ref)
        assert loaded == {"score": 0.9}

    def test_list_roundtrip(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        ref = adapter.save_sidecar("proj-1", "job-1", "mapping_detail", [{"a": 1}, {"b": 2}])
        assert ref.id == "sidecar:mapping_detail"
        loaded = adapter.load_sidecar("proj-1", "job-1", ref)
        assert loaded == [{"a": 1}, {"b": 2}]


class TestRefResolution:
    def test_resolve_raw_upload(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        adapter.save_raw_upload("proj-1", "job-1", "data.csv", b"a,b\n1,2\n")
        ref = adapter.resolve_dataset_ref("proj-1", "job-1", "raw-upload")
        assert ref is not None
        assert ref.type == "raw_upload"
        assert ref.id == "raw-upload"

    def test_resolve_normalized_dataset(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        df = pd.DataFrame({"x": [1]})
        adapter.save_normalized_dataset("proj-1", "job-1", df)
        ref = adapter.resolve_dataset_ref("proj-1", "job-1", "normalized-dataset")
        assert ref is not None
        assert ref.type == "normalized_dataset"
        assert ref.id == "normalized-dataset"

    def test_resolve_both_prefers_requested(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        adapter.save_raw_upload("proj-1", "job-1", "data.csv", b"a,b\n1,2\n")
        df = pd.DataFrame({"x": [1]})
        adapter.save_normalized_dataset("proj-1", "job-1", df)
        raw_ref = adapter.resolve_dataset_ref("proj-1", "job-1", "raw-upload")
        norm_ref = adapter.resolve_dataset_ref("proj-1", "job-1", "normalized-dataset")
        assert raw_ref is not None and raw_ref.type == "raw_upload"
        assert norm_ref is not None and norm_ref.type == "normalized_dataset"

    def test_resolve_unknown_dataset_returns_none(
        self, adapter: LocalRegularizedDatasetAdapter
    ) -> None:
        assert adapter.resolve_dataset_ref("proj-1", "job-1", "unknown") is None

    def test_resolve_missing_dataset_returns_none(
        self, adapter: LocalRegularizedDatasetAdapter
    ) -> None:
        assert adapter.resolve_dataset_ref("proj-1", "job-1", "raw-upload") is None
        assert adapter.resolve_dataset_ref("proj-1", "job-1", "normalized-dataset") is None

    def test_resolve_sidecar_ref(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        adapter.save_sidecar("proj-1", "job-1", "manifest", {"version": "1"})
        ref = adapter.resolve_sidecar_ref("proj-1", "job-1", "sidecar:manifest")
        assert ref is not None
        assert ref.sidecar_type == "manifest"
        assert ref.id == "sidecar:manifest"

    def test_resolve_unknown_sidecar_returns_none(
        self, adapter: LocalRegularizedDatasetAdapter
    ) -> None:
        assert adapter.resolve_sidecar_ref("proj-1", "job-1", "sidecar:missing") is None
        assert adapter.resolve_sidecar_ref("proj-1", "job-1", "not-a-sidecar") is None

    def test_list_sidecars_stable_ids(self, adapter: LocalRegularizedDatasetAdapter) -> None:
        adapter.save_sidecar("proj-1", "job-1", "quality", {})
        adapter.save_sidecar("proj-1", "job-1", "capability", {})
        refs1 = adapter.list_sidecars("proj-1", "job-1")
        refs2 = adapter.list_sidecars("proj-1", "job-1")
        assert len(refs1) == 2
        assert {r.id for r in refs1} == {"sidecar:quality", "sidecar:capability"}
        assert [r.id for r in refs1] == [r.id for r in refs2]
