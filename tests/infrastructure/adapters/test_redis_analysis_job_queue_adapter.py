"""Contract tests for the Redis/RQ analysis job queue adapter."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from backend.infrastructure.adapters.redis_analysis_job_queue_adapter import (
    RETAIL_ANALYSIS_WORKER_TARGET,
    RedisAnalysisJobQueueAdapter,
    serialize_queue_job_payload,
)
from backend.providers.dtos import AnalysisQueueJobPayloadDTO


def test_redis_analysis_job_queue_adapter_enqueues_json_safe_worker_payload() -> None:
    queue = _FakeQueue()
    adapter = RedisAnalysisJobQueueAdapter(queue)
    payload = AnalysisQueueJobPayloadDTO(
        project_id="project-1",
        job_id="job-1",
        trace_id="trace-1",
        trigger="retail_analysis_api",
        attempt=1,
        submitted_at="2026-05-27T10:00:00Z",
        metadata={"phase": "phase-3", "source": "adapter-test"},
    )

    handle = adapter.enqueue_project_analysis(payload)

    assert queue.calls == [
        {
            "func": RETAIL_ANALYSIS_WORKER_TARGET,
            "args": [
                {
                    "project_id": "project-1",
                    "job_id": "job-1",
                    "trace_id": "trace-1",
                    "trigger": "retail_analysis_api",
                    "attempt": 1,
                    "metadata": {"phase": "phase-3", "source": "adapter-test"},
                }
            ],
            "kwargs": {"job_id": "job-1"},
        }
    ]
    assert (
        json.loads(json.dumps(queue.calls[0]["args"][0], ensure_ascii=False))
        == queue.calls[0]["args"][0]
    )
    assert handle.job_id == "job-1"
    assert handle.queue_name == "retail-analysis"
    assert handle.status == "queued"
    assert handle.metadata["transport"] == "rq"
    assert handle.metadata["worker_target"] == RETAIL_ANALYSIS_WORKER_TARGET
    assert handle.metadata["rq_job_id"] == "job-1"


def test_serialize_queue_job_payload_uses_worker_contract_shape() -> None:
    payload = AnalysisQueueJobPayloadDTO(
        project_id="project-2",
        job_id="job-2",
        trace_id="trace-2",
        trigger="retail_analysis_api",
        attempt=2,
        resource="retail_project",
        submitted_at="2026-05-27T11:00:00Z",
        metadata={"nested": {"ok": True}},
    )

    serialized = serialize_queue_job_payload(payload)

    assert serialized == {
        "project_id": "project-2",
        "job_id": "job-2",
        "trace_id": "trace-2",
        "trigger": "retail_analysis_api",
        "attempt": 2,
        "metadata": {"nested": {"ok": True}},
    }
    assert (
        json.loads(json.dumps(asdict(payload), ensure_ascii=False))["resource"] == "retail_project"
    )
    assert "resource" not in serialized
    assert "submitted_at" not in serialized


class _FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id
        self.enqueued_at = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)


class _FakeQueue:
    def __init__(self) -> None:
        self.name = "retail-analysis"
        self.calls: list[dict[str, Any]] = []

    def enqueue(self, func: Any, *args: Any, **kwargs: Any) -> _FakeJob:
        self.calls.append({"func": func, "args": list(args), "kwargs": dict(kwargs)})
        return _FakeJob(kwargs["job_id"])
