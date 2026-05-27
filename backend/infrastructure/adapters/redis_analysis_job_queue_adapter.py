"""RQ-backed Retail analysis queue adapter."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Protocol

from backend.providers.dtos import AnalysisQueueJobHandleDTO, AnalysisQueueJobPayloadDTO

RETAIL_ANALYSIS_WORKER_TARGET = "backend.workers.retail_analysis_worker.execute_retail_analysis_job"


class QueueJobLike(Protocol):
    id: str
    enqueued_at: datetime | None


class QueueLike(Protocol):
    name: str

    def enqueue(self, func: Any, *args: Any, **kwargs: Any) -> QueueJobLike: ...


class RedisAnalysisJobQueueAdapter:
    """Queue adapter that enqueues JSON-safe worker payloads onto RQ."""

    def __init__(
        self,
        queue: QueueLike,
        worker_target: Any = RETAIL_ANALYSIS_WORKER_TARGET,
    ) -> None:
        self._queue = queue
        self._worker_target = worker_target

    def enqueue_project_analysis(
        self, payload: AnalysisQueueJobPayloadDTO
    ) -> AnalysisQueueJobHandleDTO:
        worker_payload = serialize_queue_job_payload(payload)
        job = self._queue.enqueue(self._worker_target, worker_payload, job_id=payload.job_id)
        return AnalysisQueueJobHandleDTO(
            job_id=payload.job_id,
            queue_name=self._queue.name,
            status="queued",
            enqueued_at=_isoformat(getattr(job, "enqueued_at", None)) or payload.submitted_at,
            metadata={
                **payload.metadata,
                "transport": "rq",
                "rq_job_id": getattr(job, "id", payload.job_id),
                "worker_target": _worker_target_path(self._worker_target),
            },
        )


def serialize_queue_job_payload(payload: AnalysisQueueJobPayloadDTO) -> dict[str, Any]:
    serialized = json.loads(json.dumps(asdict(payload), ensure_ascii=False))
    return {
        "project_id": serialized["project_id"],
        "job_id": serialized["job_id"],
        "trace_id": serialized["trace_id"],
        "trigger": serialized["trigger"],
        "attempt": serialized["attempt"],
        "metadata": serialized.get("metadata") or {},
    }


def _worker_target_path(worker_target: Any) -> str:
    module = getattr(worker_target, "__module__", "")
    name = getattr(worker_target, "__name__", str(worker_target))
    return f"{module}.{name}".strip(".")


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")
