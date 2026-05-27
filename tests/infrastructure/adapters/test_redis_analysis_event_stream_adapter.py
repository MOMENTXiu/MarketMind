"""Contract tests for the Redis analysis event stream adapter."""

from __future__ import annotations

import json

from backend.infrastructure.adapters.redis_analysis_event_stream_adapter import (
    RedisAnalysisEventStreamAdapter,
    deserialize_subscription_item,
    serialize_subscription_item,
)
from backend.providers.analysis_event_stream_provider import project_channel
from backend.providers.dtos import AnalysisStateEventDTO


def test_redis_analysis_event_stream_adapter_serializes_and_replays_project_events() -> None:
    redis_client = _FakeRedisClient()
    adapter = RedisAnalysisEventStreamAdapter(
        redis_client,
        heartbeat_interval_ms=15000,
        retry_ms=3000,
    )
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
        metadata={"source": "adapter-test"},
    )

    published = adapter.publish_event(event)
    replayed = list(adapter.subscribe_project_events("project-1"))
    serialized = json.loads(redis_client.published[project_channel("project-1")][0])

    assert published.retry_ms == 3000
    assert published.reconnect_ms == 3000
    assert published.metadata["heartbeat_interval_ms"] == 15000
    assert serialized["event"] == "state_changed"
    assert serialized["fallback_url"] == "/api/analysis/projects/project-1"
    assert replayed == [published]


def test_subscription_item_round_trips_json_safely() -> None:
    redis_client = _FakeRedisClient()
    adapter = RedisAnalysisEventStreamAdapter(redis_client)
    heartbeat = adapter.publish_event(
        AnalysisStateEventDTO(
            event="heartbeat",
            resource="retail_project",
            channel=project_channel("project-2"),
            resource_id="project-2",
            project_id="project-2",
            status="processing",
            payload={"status": "processing"},
            fallback_url="/api/analysis/projects/project-2",
            occurred_at="2026-05-27T10:15:00Z",
        )
    )

    restored = deserialize_subscription_item(serialize_subscription_item(heartbeat))

    assert restored == heartbeat
    assert restored.heartbeat is True


def test_random_event_ids_do_not_filter_live_pubsub_events_after_last_event_id() -> None:
    redis_client = _FakeRedisClient()
    adapter = RedisAnalysisEventStreamAdapter(redis_client)
    adapter.publish_event(
        AnalysisStateEventDTO(
            event="state_changed",
            resource="retail_project",
            channel=project_channel("project-3"),
            resource_id="project-3",
            project_id="project-3",
            status="processing",
            payload={"status": "processing"},
            fallback_url="/api/analysis/projects/project-3",
            metadata={"event_id": "a-random-live-event"},
        )
    )

    replayed = list(adapter.subscribe_project_events("project-3", last_event_id="z-last-seen"))

    assert len(replayed) == 1
    assert replayed[0].event_id == "a-random-live-event"


class _FakePubSub:
    def __init__(self, client: "_FakeRedisClient") -> None:
        self._client = client
        self._channels: list[str] = []

    def subscribe(self, *channels: str) -> None:
        self._channels.extend(channels)

    def listen(self):
        for channel in self._channels:
            for payload in self._client.published.get(channel, []):
                yield {"type": "message", "channel": channel, "data": payload}

    def close(self) -> None:
        return None


class _FakeRedisClient:
    def __init__(self) -> None:
        self.published: dict[str, list[str]] = {}

    def publish(self, channel: str, message: str) -> int:
        self.published.setdefault(channel, []).append(message)
        return 1

    def pubsub(self, ignore_subscribe_messages: bool = True) -> _FakePubSub:
        assert ignore_subscribe_messages is True
        return _FakePubSub(self)
