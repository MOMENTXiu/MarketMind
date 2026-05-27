"""Analysis job queue provider interface for durable worker payloads."""

from __future__ import annotations

from typing import Protocol

from backend.providers.dtos import AnalysisQueueJobHandleDTO, AnalysisQueueJobPayloadDTO


class AnalysisJobQueueProvider(Protocol):
    def enqueue_project_analysis(
        self, payload: AnalysisQueueJobPayloadDTO
    ) -> AnalysisQueueJobHandleDTO:
        """Enqueue one durable Retail analysis job payload."""


class InMemoryAnalysisJobQueueProvider:
    """Transitional in-memory queue used for contract tests and container assembly."""

    def __init__(self, queue_name: str = "in-memory-analysis") -> None:
        self.queue_name = queue_name
        self.payloads: list[AnalysisQueueJobPayloadDTO] = []
        self.handles: list[AnalysisQueueJobHandleDTO] = []

    def enqueue_project_analysis(
        self, payload: AnalysisQueueJobPayloadDTO
    ) -> AnalysisQueueJobHandleDTO:
        handle = AnalysisQueueJobHandleDTO(
            job_id=payload.job_id,
            queue_name=self.queue_name,
            status="queued",
            enqueued_at=payload.submitted_at,
            metadata={**payload.metadata, "transport": "in-memory"},
        )
        self.payloads.append(payload)
        self.handles.append(handle)
        return handle
