"""Contract tests for local file and generated asset adapters."""

from __future__ import annotations

from backend.infrastructure.adapters.local_generated_asset_adapter import (
    LocalGeneratedAssetAdapter,
)
from backend.infrastructure.adapters.local_project_file_storage_adapter import (
    LocalProjectFileStorageAdapter,
)
from backend.providers.dtos import UploadedFileDTO


def test_local_project_file_storage_preserves_project_file_layout(tmp_path) -> None:
    adapter = LocalProjectFileStorageAdapter(str(tmp_path / "data"))

    dataset = adapter.save_uploaded_dataset(
        "project-1",
        UploadedFileDTO(filename="source.xlsx", content_type="application/vnd.ms-excel"),
        b"a,b\n1,2\n",
    )
    assert dataset.path == tmp_path / "data/projects/project-1/dataset.csv"
    assert dataset.filename == "source.xlsx"
    resolved_dataset = adapter.resolve_dataset("project-1")
    assert resolved_dataset is not None
    assert resolved_dataset.path == dataset.path
    assert resolved_dataset.filename == "dataset.csv"

    customer_asset = adapter.write_customers(
        "project-1",
        [{"客户ID": "C001", "客户分群": 2}],
    )
    assert customer_asset.path == tmp_path / "data/projects/project-1/customers.csv"
    assert adapter.read_customers("project-1") == [{"客户ID": "C001", "客户分群": 2}]
    assert adapter.read_customers("missing") == []
    assert adapter.resolve_dataset("missing") is None


def test_local_generated_asset_adapter_preserves_asset_paths_and_urls(tmp_path) -> None:
    adapter = LocalGeneratedAssetAdapter(
        data_dir=str(tmp_path / "data"),
        outputs_dir=str(tmp_path / "outputs"),
    )

    report = adapter.save_project_report("project-1", "report_project-1.md", "# report")
    assert report.path == tmp_path / "data/projects/project-1/outputs/reports/report_project-1.md"
    assert adapter.resolve_project_report("project-1") == report
