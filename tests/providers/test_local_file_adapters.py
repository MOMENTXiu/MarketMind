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
        ai_audio_dir=str(tmp_path / "backend/data/audio"),
        temp_dir=str(tmp_path / "tmp"),
    )

    report = adapter.save_project_report("project-1", "report_project-1.md", "# report")
    assert report.path == tmp_path / "data/projects/project-1/outputs/reports/report_project-1.md"
    assert adapter.resolve_project_report("project-1") == report

    source_audio = tmp_path / "source.mp3"
    source_audio.write_bytes(b"audio")
    project_audio = adapter.save_project_audio("project-1", "report_project-1.mp3", source_audio)
    assert (
        project_audio.path
        == tmp_path / "data/projects/project-1/outputs/audio/report_project-1.mp3"
    )
    assert adapter.resolve_project_audio("project-1") == project_audio

    public_audio = adapter.save_public_audio("tts_1.mp3", source_audio)
    assert public_audio.path == tmp_path / "outputs/audio/tts_1.mp3"
    assert public_audio.url == "/outputs/audio/tts_1.mp3"

    temp_audio_dir = tmp_path / "tmp"
    temp_audio_dir.mkdir()
    temp_audio = temp_audio_dir / "voice.mp3"
    temp_audio.write_bytes(b"temp")
    data_audio_dir = tmp_path / "backend/data/audio"
    data_audio_dir.mkdir(parents=True)
    data_audio = data_audio_dir / "voice.mp3"
    data_audio.write_bytes(b"data")
    assert adapter.resolve_ai_audio("voice.mp3").path == temp_audio

    temp_audio.unlink()
    assert adapter.resolve_ai_audio("voice.mp3").path == data_audio
    assert adapter.resolve_ai_audio("missing.mp3") is None
