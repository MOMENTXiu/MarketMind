"""Redis pub/sub adapter for SSE-safe analysis events."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict
from typing import Any, Protocol
from uuid import uuid4

from backend.providers.analysis_event_stream_provider import job_channel, project_channel
from backend.providers.dtos import AnalysisEventSubscriptionItemDTO, AnalysisStateEventDTO


class RedisPubSubLike(Protocol):
    def subscribe(self, *channels: str) -> None: ...

    def listen(self) -> Iterator[dict[str, Any]]: ...

    def close(self) -> None: ...


class RedisClientLike(Protocol):
    def publish(self, channel: str, message: str) -> Any: ...

    def pubsub(self, ignore_subscribe_messages: bool = True) -> RedisPubSubLike: ...


class RedisAnalysisEventStreamAdapter:
    """AnalysisEventStreamProvider backed by Redis pub/sub."""

    def __init__(
        self,
        redis_client: RedisClientLike,
        *,
        heartbeat_interval_ms: int = 15000,
        retry_ms: int = 3000,
    ) -> None:
        self._redis = redis_client
        self._heartbeat_interval_ms = heartbeat_interval_ms
        self._retry_ms = retry_ms

    def publish_event(self, event: AnalysisStateEventDTO) -> AnalysisEventSubscriptionItemDTO:
        item = build_subscription_item(
            event,
            heartbeat_interval_ms=self._heartbeat_interval_ms,
            retry_ms=self._retry_ms,
        )
        self._redis.publish(item.channel, serialize_subscription_item(item))
        return item

    def subscribe_project_events(
        self,
        project_id: str,
        last_event_id: str | None = None,
    ) -> Iterator[AnalysisEventSubscriptionItemDTO]:
        return self._subscribe(project_channel(project_id), last_event_id)

    def subscribe_job_events(
        self,
        job_id: str,
        last_event_id: str | None = None,
    ) -> Iterator[AnalysisEventSubscriptionItemDTO]:
        return self._subscribe(job_channel(job_id), last_event_id)

    def _subscribe(
        self,
        channel: str,
        last_event_id: str | None,
    ) -> Iterator[AnalysisEventSubscriptionItemDTO]:
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(channel)
        try:
            for message in pubsub.listen():
                if not _is_pubsub_message(message):
                    continue
                item = deserialize_subscription_item(message.get("data"))
                if item.channel != channel:
                    continue
                if _is_after(item.event_id, last_event_id):
                    yield item
        finally:
            close = getattr(pubsub, "close", None)
            if callable(close):
                close()


def build_subscription_item(
    event: AnalysisStateEventDTO,
    *,
    heartbeat_interval_ms: int,
    retry_ms: int,
) -> AnalysisEventSubscriptionItemDTO:
    metadata = dict(event.metadata)
    effective_heartbeat = event.heartbeat_interval_ms or heartbeat_interval_ms
    effective_retry = event.retry_ms if event.retry_ms is not None else retry_ms
    metadata.setdefault("heartbeat_interval_ms", effective_heartbeat)
    event_id = str(metadata.get("event_id") or uuid4().hex)
    return AnalysisEventSubscriptionItemDTO(
        event_id=event_id,
        event=event.event,
        resource=event.resource,
        channel=event.channel,
        resource_id=event.resource_id,
        project_id=event.project_id,
        job_id=event.job_id,
        trace_id=event.trace_id,
        status=event.status,
        stage=event.stage,
        payload=_json_safe(event.payload),
        fallback_url=event.fallback_url,
        occurred_at=event.occurred_at,
        heartbeat=event.event == "heartbeat",
        retry_ms=effective_retry,
        reconnect_ms=effective_retry,
        terminal=event.terminal,
        metadata=_json_safe(metadata),
    )


def serialize_subscription_item(item: AnalysisEventSubscriptionItemDTO) -> str:
    return json.dumps(asdict(item), ensure_ascii=False)


def deserialize_subscription_item(message: Any) -> AnalysisEventSubscriptionItemDTO:
    if isinstance(message, bytes):
        message = message.decode("utf-8")
    if isinstance(message, dict):
        payload = message
    else:
        payload = json.loads(str(message))
    return AnalysisEventSubscriptionItemDTO(**payload)


def _is_after(event_id: str | None, last_event_id: str | None) -> bool:
    if last_event_id is None or event_id is None:
        return True
    try:
        return int(event_id) > int(last_event_id)
    except ValueError:
        return True


def _is_pubsub_message(message: dict[str, Any]) -> bool:
    if not isinstance(message, dict):
        return False
    message_type = message.get("type")
    return message_type in {None, "message", "pmessage"}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))
