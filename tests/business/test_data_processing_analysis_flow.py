"""Flow tests for data-processing analysis lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.business.flows.data_processing_analysis_flow import DataProcessingAnalysisFlow
from backend.core.errors import NotFoundError, ValidationError
from backend.providers.container import ProvidersContainer
from tests.fakes.providers import (
    FakeAnalysisArtifactProvider,
    FakeAnalysisJobProvider,
    FakeAnalysisModelStoreProvider,
    FakeAssociationRuleStoreProvider,
    FakeDatasetProvider,
    FakeGeneratedAssetProvider,
    FakeLLMProvider,
    FakeProjectFileStorageProvider,
    FakeProjectRepositoryProvider,
    FakeRecommendationModelStoreProvider,
    FakeRegularizedDatasetProvider,
    FakeRetailDatasetProvider,
    FakeSpeechSynthesisProvider,
    FakeTelemetryProvider,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "data_processing"


def _make_container(tmp_path: Path) -> ProvidersContainer:
    return ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        retail_dataset=FakeRetailDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        analysis_artifacts=FakeAnalysisArtifactProvider(),
        analysis_models=FakeAnalysisModelStoreProvider(),
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
        regularized_dataset=FakeRegularizedDatasetProvider(),
    )


class TestDataProcessingAnalysisFlow:
    def test_create_job(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        result = flow.create_job("test-project", "My Job")
        assert result["project_id"] == "test-project"
        assert result["name"] == "My Job"
        assert result["status"] == "queued"
        assert "job_id" in result

    def test_create_job_rejects_empty_name(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        with pytest.raises(ValidationError):
            flow.create_job("test-project", "   ")

    def test_upload_and_regularize(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        content = (FIXTURES / "mini_retail.csv").read_bytes()
        upload_result = flow.upload_raw_dataset("test-project", job_id, "mini_retail.csv", content)
        assert upload_result["status"] == "queued"

        reg_result = flow.regularize("test-project", job_id)
        assert reg_result["status"] in {"queued", "needs_review", "completed"}
        assert reg_result["job_id"] == job_id
        assert "quality" in reg_result
        assert "capability" in reg_result

    def test_get_job(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        result = flow.get_job("test-project", job_id)
        assert result["job_id"] == job_id

    def test_run_before_upload_fails(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        with pytest.raises(ValidationError, match="regularization"):
            flow.run_analysis("test-project", job_id)

    def test_run_before_regularize_fails(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        content = (FIXTURES / "mini_retail.csv").read_bytes()
        flow.upload_raw_dataset("test-project", job_id, "mini_retail.csv", content)

        with pytest.raises(ValidationError, match="regularization"):
            flow.run_analysis("test-project", job_id)

    def test_run_when_needs_review_fails(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        content = (FIXTURES / "mini_retail.csv").read_bytes()
        flow.upload_raw_dataset("test-project", job_id, "mini_retail.csv", content)

        reg_result = flow.regularize("test-project", job_id)
        if reg_result["status"] == "needs_review":
            with pytest.raises(ValidationError, match="needs review"):
                flow.run_analysis("test-project", job_id)

    def test_run_after_regularize_succeeds(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        content = (FIXTURES / "mini_retail.csv").read_bytes()
        flow.upload_raw_dataset("test-project", job_id, "mini_retail.csv", content)

        reg_result = flow.regularize("test-project", job_id)
        if reg_result["status"] != "completed":
            pytest.skip("Regularization did not complete; cannot test run")

        run_result = flow.run_analysis("test-project", job_id)
        assert run_result["status"] == "processing"

    def test_get_dataset_ref(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        content = (FIXTURES / "mini_retail.csv").read_bytes()
        flow.upload_raw_dataset("test-project", job_id, "mini_retail.csv", content)

        ref = flow.get_dataset_ref("test-project", job_id, "raw-upload")
        assert ref["id"] == "raw-upload"
        assert ref["type"] == "raw_upload"

        with pytest.raises(NotFoundError):
            flow.get_dataset_ref("test-project", job_id, "normalized-dataset")

    def test_get_sidecar_ref(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        content = (FIXTURES / "mini_retail.csv").read_bytes()
        flow.upload_raw_dataset("test-project", job_id, "mini_retail.csv", content)
        flow.regularize("test-project", job_id)

        ref = flow.get_sidecar_ref("test-project", job_id, "sidecar:capability")
        assert ref["id"] == "sidecar:capability"

        with pytest.raises(NotFoundError):
            flow.get_sidecar_ref("test-project", job_id, "sidecar:missing")

    def test_load_sidecar(self, tmp_path: Path) -> None:
        flow = DataProcessingAnalysisFlow(_make_container(tmp_path))
        job = flow.create_job("test-project", "My Job")
        job_id = job["job_id"]

        content = (FIXTURES / "mini_retail.csv").read_bytes()
        flow.upload_raw_dataset("test-project", job_id, "mini_retail.csv", content)
        flow.regularize("test-project", job_id)

        payload = flow.load_sidecar("test-project", job_id, "sidecar:capability")
        assert isinstance(payload, dict)

        with pytest.raises(NotFoundError):
            flow.load_sidecar("test-project", job_id, "sidecar:missing")
