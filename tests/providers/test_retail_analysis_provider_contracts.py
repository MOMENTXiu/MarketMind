"""Contract tests for Retail V2 migration provider boundary anchors."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow
from backend.providers.analysis_event_stream_provider import job_channel, project_channel
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import (
    AnalysisQueueJobPayloadDTO,
    AnalysisStateEventDTO,
    RetailAnalysisProjectStateDTO,
    RetailAnalysisRunInfoDTO,
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


def test_retail_analysis_state_provider_contract_supports_save_get_list_and_delete() -> None:
    provider = FakeRetailAnalysisStateProvider()
    first = _state("project-1", created_at="2026-05-27T09:00:00Z")
    second = _state("project-2", created_at="2026-05-27T10:00:00Z")

    provider.save_state(first)
    provider.save_state(second)
    saved = provider.save_run_info("project-1", _run_info("job-1", "trace-1", status="processing"))

    assert saved is not None
    assert saved.run_info is not None
    assert provider.get_state("project-1") == saved
    assert [project.id for project in provider.list_projects()] == ["project-2", "project-1"]
    listed = provider.list_projects()[1]
    assert listed.run_info is not None
    assert listed.dataset_filename == "retail_sales.csv"
    assert listed.dataset_ref == {"id": "dataset-1", "type": "dataset", "name": "retail_sales.csv"}
    assert listed.stage_statuses == [{"stage": "dataset_preparation", "status": "queued"}]
    assert listed.summary == {"records": 0}
    assert listed.quality_summary == {"grade": "A"}
    assert listed.artifact_refs == [{"id": "table-1", "type": "table", "name": "segments.csv"}]
    assert listed.recommendations == [{"item": "milk", "score": 0.9}]
    assert listed.marketer_insights == {"segments": []}
    assert listed.job_id == "job-1"
    assert listed.trace_id == "trace-1"
    assert provider.delete_project("project-1") is True
    assert provider.delete_project("project-1") is False
    assert [project.id for project in provider.list_projects()] == ["project-2"]


def test_analysis_job_queue_provider_contract_uses_json_serializable_worker_payload() -> None:
    provider = FakeAnalysisJobQueueProvider()
    payload = AnalysisQueueJobPayloadDTO(
        project_id="project-1",
        job_id="job-1",
        trace_id="trace-1",
        trigger="retail_analysis_api",
        attempt=1,
        submitted_at="2026-05-27T10:00:00Z",
        metadata={"phase": "phase-2", "source": "provider-contract"},
    )

    serialized = json.loads(json.dumps(asdict(payload), ensure_ascii=False))
    handle = provider.enqueue_project_analysis(payload)

    assert serialized == {
        "project_id": "project-1",
        "job_id": "job-1",
        "trace_id": "trace-1",
        "trigger": "retail_analysis_api",
        "attempt": 1,
        "resource": "retail_project",
        "submitted_at": "2026-05-27T10:00:00Z",
        "metadata": {"phase": "phase-2", "source": "provider-contract"},
    }
    assert provider.payloads == [payload]
    assert handle.job_id == payload.job_id
    assert handle.queue_name == "in-memory-analysis"
    assert handle.metadata["transport"] == "in-memory"


def test_analysis_event_stream_contract_preserves_payload_fallback_and_heartbeat_metadata() -> None:
    provider = FakeAnalysisEventStreamProvider()
    event = AnalysisStateEventDTO(
        event="state_changed",
        resource="retail_project",
        channel=project_channel("project-1"),
        resource_id="project-1",
        project_id="project-1",
        job_id="job-1",
        trace_id="trace-1",
        status="processing",
        stage="dataset_preparation",
        payload={"status": "processing", "stage": "dataset_preparation"},
        fallback_url="/api/analysis/projects/project-1",
        occurred_at="2026-05-27T10:00:00Z",
        heartbeat_interval_ms=15000,
        retry_ms=3000,
        metadata={"source": "contract-test"},
    )
    heartbeat = AnalysisStateEventDTO(
        event="heartbeat",
        resource="retail_project",
        channel=project_channel("project-1"),
        resource_id="project-1",
        project_id="project-1",
        status="processing",
        payload={"status": "processing"},
        fallback_url="/api/analysis/projects/project-1",
        occurred_at="2026-05-27T10:00:15Z",
        heartbeat_interval_ms=15000,
        retry_ms=3000,
    )

    provider.publish_event(event)
    provider.publish_event(heartbeat)
    items = list(provider.subscribe_project_events("project-1"))
    serialized = json.loads(json.dumps([asdict(item) for item in items], ensure_ascii=False))

    assert len(items) == 2
    assert items[0].fallback_url == "/api/analysis/projects/project-1"
    assert items[0].retry_ms == 3000
    assert items[0].reconnect_ms == 3000
    assert items[0].metadata["heartbeat_interval_ms"] == 15000
    assert items[1].heartbeat is True
    assert serialized[0]["payload"]["stage"] == "dataset_preparation"


def test_analysis_event_stream_contract_supports_data_processing_needs_review_events() -> None:
    provider = FakeAnalysisEventStreamProvider()
    event = AnalysisStateEventDTO(
        event="needs_review",
        resource="data_processing_job",
        channel=job_channel("job-22"),
        resource_id="job-22",
        job_id="job-22",
        trace_id="trace-22",
        status="needs_review",
        payload={"status": "needs_review", "quality": {"grade": "C"}},
        fallback_url="/api/analysis/jobs/job-22",
        occurred_at="2026-05-27T10:05:00Z",
        retry_ms=3000,
    )

    provider.publish_event(event)
    items = list(provider.subscribe_job_events("job-22"))

    assert len(items) == 1
    assert items[0].event == "needs_review"
    assert items[0].resource == "data_processing_job"
    assert items[0].fallback_url == "/api/analysis/jobs/job-22"
    assert items[0].payload["quality"] == {"grade": "C"}


def test_phase6_cutover_removes_pickle_state_and_index_io(tmp_path: Path) -> None:
    container = ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        retail_dataset=FakeRetailDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        analysis_artifacts=FakeAnalysisArtifactProvider(),
        analysis_models=_RejectingRetailStateModelStore(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
        regularized_dataset=FakeRegularizedDatasetProvider(),
        retail_analysis_state=FakeRetailAnalysisStateProvider(),
        analysis_job_queue=FakeAnalysisJobQueueProvider(),
        analysis_event_stream=FakeAnalysisEventStreamProvider(),
    )

    flow = RetailAnalysisFlow(container)

    project = flow.create_project("Phase 6 Cutover Anchor")
    listed = flow.list_projects()
    deleted = flow.delete_project(project["id"])

    assert listed["total"] == 1
    assert listed["projects"][0]["id"] == project["id"]
    assert deleted == {
        "project_id": project["id"],
        "deleted": True,
        "deleted_models": 0,
    }


def _state(project_id: str, created_at: str) -> RetailAnalysisProjectStateDTO:
    return RetailAnalysisProjectStateDTO(
        id=project_id,
        name=f"Project {project_id}",
        description="contract state",
        status="queued",
        stage_statuses=[{"stage": "dataset_preparation", "status": "queued"}],
        summary={"records": 0},
        dataset_ref={"id": "dataset-1", "type": "dataset", "name": "retail_sales.csv"},
        quality_summary={"grade": "A"},
        artifact_refs=[{"id": "table-1", "type": "table", "name": "segments.csv"}],
        recommendations=[{"item": "milk", "score": 0.9}],
        marketer_insights={"segments": []},
        created_at=created_at,
        updated_at=created_at,
    )


def _run_info(job_id: str, trace_id: str, status: str) -> RetailAnalysisRunInfoDTO:
    return RetailAnalysisRunInfoDTO(
        job_id=job_id,
        trace_id=trace_id,
        trigger="retail_analysis_api",
        attempt=1,
        status=status,
        created_at="2026-05-27T10:00:00Z",
        updated_at="2026-05-27T10:00:00Z",
        metadata={"source": "contract-test"},
    )


class _RejectingRetailStateModelStore(FakeAnalysisModelStoreProvider):
    def save_model(
        self,
        project_id: str,
        model_type: str,
        payload: Any,
        version: str = "current",
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        self._reject(model_type)
        return super().save_model(project_id, model_type, payload, version, metadata)

    def load_model(self, project_id: str, model_type: str, version: str = "current") -> Any | None:
        self._reject(model_type)
        return super().load_model(project_id, model_type, version)

    def delete_model(self, project_id: str, model_type: str, version: str = "current") -> bool:
        self._reject(model_type)
        return super().delete_model(project_id, model_type, version)

    @staticmethod
    def _reject(model_type: str) -> None:
        if model_type in {"retail_analysis_project_index", "retail_analysis_project_state"}:
            raise AssertionError("pickle state/index access must be removed in Phase 6")
