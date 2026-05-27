"""Dry-run and payload validation tests for the Retail analysis worker."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow
from backend.core.config import Settings
from backend.core.errors import ValidationError
from backend.infrastructure.adapters.redis_analysis_job_queue_adapter import (
    serialize_queue_job_payload,
)
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisQueueJobPayloadDTO
from backend.workers.retail_analysis_worker import (
    execute_retail_analysis_job,
    validate_retail_analysis_job_payload,
)
from tests.fakes.providers import (
    FakeAnalysisArtifactProvider,
    FakeAnalysisEventStreamProvider,
    FakeAnalysisJobProvider,
    FakeAnalysisJobQueueProvider,
    FakeAnalysisModelStoreProvider,
    FakeAssociationRuleStoreProvider,
    FakeDatasetProvider,
    FakeGeneratedAssetProvider,
    FakeLLMProvider,
    FakeProjectFileStorageProvider,
    FakeProjectRepositoryProvider,
    FakeRecommendationModelStoreProvider,
    FakeRegularizedDatasetProvider,
    FakeRetailAnalysisStateProvider,
    FakeRetailDatasetProvider,
    FakeTelemetryProvider,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_FIXTURE = ROOT / "tests" / "fixtures" / "analysis_v2" / "retail_sales_raw_gbk.csv"


def test_validate_retail_analysis_job_payload_rejects_invalid_payload() -> None:
    with pytest.raises(ValidationError):
        validate_retail_analysis_job_payload(
            {
                "project_id": "project-1",
                "trace_id": "trace-1",
                "trigger": "retail_analysis_api",
                "attempt": 0,
                "metadata": {},
            }
        )


def test_execute_retail_analysis_job_dry_run_builds_phase3_providers() -> None:
    payload = serialize_queue_job_payload(
        AnalysisQueueJobPayloadDTO(
            project_id="project-1",
            job_id="job-1",
            trace_id="trace-1",
            trigger="retail_analysis_api",
            attempt=1,
            metadata={"phase": "phase-3"},
        )
    )

    result = execute_retail_analysis_job(
        payload,
        dry_run=True,
        settings=Settings(
            _env_file=None,
            TASK_QUEUE_BACKEND="redis",
            REDIS_ENABLED=True,
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            REDIS_URL="redis://localhost:6379/9",
        ),
    )

    assert result == {
        "status": "dry_run",
        "project_id": "project-1",
        "job_id": "job-1",
        "trace_id": "trace-1",
        "attempt": 1,
        "task_queue_backend": "redis",
        "providers": {
            "retail_analysis_state": "PostgresRetailAnalysisStateAdapter",
            "analysis_job_queue": "RedisAnalysisJobQueueAdapter",
            "analysis_event_stream": "RedisAnalysisEventStreamAdapter",
        },
    }


def test_execute_retail_analysis_job_non_dry_run_uses_business_entry(tmp_path: Path) -> None:
    container = ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        retail_dataset=FakeRetailDatasetProvider(),
        regularized_dataset=FakeRegularizedDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        analysis_artifacts=FakeAnalysisArtifactProvider(),
        analysis_models=FakeAnalysisModelStoreProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
        retail_analysis_state=FakeRetailAnalysisStateProvider(),
        analysis_job_queue=FakeAnalysisJobQueueProvider(),
        analysis_event_stream=FakeAnalysisEventStreamProvider(),
    )
    flow = RetailAnalysisFlow(container)
    project = flow.create_project("Worker Flow", "non dry run")
    flow.upload_dataset(project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())
    run = flow.start_analysis(project["id"])

    result = execute_retail_analysis_job(
        {
            "project_id": project["id"],
            "job_id": run["job_id"],
            "trace_id": run["trace_id"],
            "trigger": "retail_analysis_api",
            "attempt": 1,
            "metadata": {},
        },
        settings=Settings(_env_file=None),
        provider_factory=lambda *_args, **_kwargs: container,
    )

    stored = flow.get_project(project["id"])

    assert result["status"] == "completed"
    assert stored["status"] in {"completed", "failed"}
    assert stored["status"] != "processing"


def test_execute_retail_analysis_job_rejects_stale_payload_without_mutating_state(
    tmp_path: Path,
) -> None:
    container = ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        retail_dataset=FakeRetailDatasetProvider(),
        regularized_dataset=FakeRegularizedDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        analysis_artifacts=FakeAnalysisArtifactProvider(),
        analysis_models=FakeAnalysisModelStoreProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
        retail_analysis_state=FakeRetailAnalysisStateProvider(),
        analysis_job_queue=FakeAnalysisJobQueueProvider(),
        analysis_event_stream=FakeAnalysisEventStreamProvider(),
    )
    flow = RetailAnalysisFlow(container)
    project = flow.create_project("Worker Flow", "stale payload")
    flow.upload_dataset(project["id"], RAW_FIXTURE.name, RAW_FIXTURE.read_bytes())
    run = flow.start_analysis(project["id"])
    before = flow.get_project(project["id"])

    with pytest.raises(ValidationError):
        execute_retail_analysis_job(
            {
                "project_id": project["id"],
                "job_id": "stale-job",
                "trace_id": run["trace_id"],
                "trigger": "retail_analysis_api",
                "attempt": 1,
                "metadata": {},
            },
            settings=Settings(_env_file=None, TASK_QUEUE_BACKEND="none", REDIS_ENABLED=False),
            provider_factory=lambda *_args, **_kwargs: container,
        )

    after = flow.get_project(project["id"])
    assert after["status"] == before["status"] == "processing"
    assert after["job_id"] == before["job_id"]
    assert after["trace_id"] == before["trace_id"]
