"""Pipeline contract tests for DatasetUploadPipeline."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from backend.business.pipelines.dataset_upload_pipeline import (
    DatasetUploadPipeline,
    UploadedFile,
)
from backend.core.errors import NotFoundError, ValidationError
from backend.models.project import ProjectCreate, ProjectStatus
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


def _make_container(tmp_path: Path) -> tuple[ProvidersContainer, FakeAnalysisJobProvider]:
    jobs = FakeAnalysisJobProvider()
    container = ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=jobs,
        telemetry=FakeTelemetryProvider(),
    )
    return container, jobs


def test_upload_persists_dataset_and_submits_job(tmp_path: Path) -> None:
    container, jobs = _make_container(tmp_path)
    project = container.repository.create_project(ProjectCreate(name="demo"))
    pipeline = DatasetUploadPipeline(container)

    result = pipeline.upload(
        project.id,
        UploadedFile(filename="data.csv", stream=io.BytesIO(b"col1\n1\n")),
    )

    assert result.status == ProjectStatus.PROCESSING
    assert Path(result.dataset_path).exists()
    stored = container.repository.get_project(project.id)
    assert stored is not None
    assert stored.status == ProjectStatus.PROCESSING
    assert stored.dataset_filename == "data.csv"
    assert len(jobs.jobs) == 1
    assert jobs.jobs[0].trigger == "upload"


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    container, _ = _make_container(tmp_path)
    project = container.repository.create_project(ProjectCreate(name="demo"))
    pipeline = DatasetUploadPipeline(container)
    with pytest.raises(ValidationError):
        pipeline.upload(
            project.id,
            UploadedFile(filename="data.txt", stream=io.BytesIO(b"x")),
        )


def test_upload_missing_project_raises_not_found(tmp_path: Path) -> None:
    container, _ = _make_container(tmp_path)
    pipeline = DatasetUploadPipeline(container)
    with pytest.raises(NotFoundError):
        pipeline.upload(
            "missing",
            UploadedFile(filename="data.csv", stream=io.BytesIO(b"x")),
        )


def test_reanalyze_without_dataset_raises_validation(tmp_path: Path) -> None:
    container, _ = _make_container(tmp_path)
    project = container.repository.create_project(ProjectCreate(name="demo"))
    pipeline = DatasetUploadPipeline(container)
    with pytest.raises(ValidationError):
        pipeline.reanalyze(project.id)


def test_reanalyze_submits_job(tmp_path: Path) -> None:
    container, jobs = _make_container(tmp_path)
    project = container.repository.create_project(ProjectCreate(name="demo"))
    pipeline = DatasetUploadPipeline(container)
    pipeline.upload(project.id, UploadedFile(filename="data.csv", stream=io.BytesIO(b"x")))
    jobs.jobs.clear()
    pipeline.reanalyze(project.id)
    assert len(jobs.jobs) == 1
    assert jobs.jobs[0].trigger == "reanalyze"
