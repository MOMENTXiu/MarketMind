"""Analysis event stream provider interface for SSE-safe event contracts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from typing import Protocol

from backend.providers.dtos import AnalysisEventSubscriptionItemDTO, AnalysisStateEventDTO


class AnalysisEventStreamProvider(Protocol):
    def publish_event(self, event: AnalysisStateEventDTO) -> AnalysisEventSubscriptionItemDTO:
        """Publish one JSON-safe analysis state event."""

    def subscribe_project_events(
        self,
        project_id: str,
        last_event_id: str | None = None,
    ) -> Iterator[AnalysisEventSubscriptionItemDTO]:
        """Yield project-scoped SSE items after one optional event id."""

    def subscribe_job_events(
        self,
        job_id: str,
        last_event_id: str | None = None,
    ) -> Iterator[AnalysisEventSubscriptionItemDTO]:
        """Yield job-scoped SSE items after one optional event id."""


class InMemoryAnalysisEventStreamProvider:
    """Transitional in-memory event stream used for contract tests and assembly."""

    def __init__(self) -> None:
        self._events: dict[str, list[AnalysisEventSubscriptionItemDTO]] = defaultdict(list)
        self._sequence = 0

    def publish_event(self, event: AnalysisStateEventDTO) -> AnalysisEventSubscriptionItemDTO:
        self._sequence += 1
        metadata = dict(event.metadata)
        if event.heartbeat_interval_ms is not None:
            metadata["heartbeat_interval_ms"] = event.heartbeat_interval_ms

        item = AnalysisEventSubscriptionItemDTO(
            event_id=str(self._sequence),
            event=event.event,
            resource=event.resource,
            channel=event.channel,
            resource_id=event.resource_id,
            project_id=event.project_id,
            job_id=event.job_id,
            trace_id=event.trace_id,
            status=event.status,
            stage=event.stage,
            payload=event.payload,
            fallback_url=event.fallback_url,
            occurred_at=event.occurred_at,
            heartbeat=event.event == "heartbeat",
            retry_ms=event.retry_ms,
            reconnect_ms=event.retry_ms,
            terminal=event.terminal,
            metadata=metadata,
        )
        self._events[event.channel].append(item)
        return item

    def subscribe_project_events(
        self,
        project_id: str,
        last_event_id: str | None = None,
    ) -> Iterator[AnalysisEventSubscriptionItemDTO]:
        return self._iter_channel(project_channel(project_id), last_event_id)

    def subscribe_job_events(
        self,
        job_id: str,
        last_event_id: str | None = None,
    ) -> Iterator[AnalysisEventSubscriptionItemDTO]:
        return self._iter_channel(job_channel(job_id), last_event_id)

    def _iter_channel(
        self,
        channel: str,
        last_event_id: str | None,
    ) -> Iterator[AnalysisEventSubscriptionItemDTO]:
        for item in self._events.get(channel, []):
            if _is_after(item.event_id, last_event_id):
                yield item


def project_channel(project_id: str) -> str:
    return f"marketmind:analysis:project:{project_id}"


def job_channel(job_id: str) -> str:
    return f"marketmind:analysis:job:{job_id}"


def _is_after(event_id: str | None, last_event_id: str | None) -> bool:
    if last_event_id is None or event_id is None:
        return True
    try:
        return int(event_id) > int(last_event_id)
    except ValueError:
        return True
