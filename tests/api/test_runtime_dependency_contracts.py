"""Runtime dependency contracts for default API provider assembly."""

from __future__ import annotations

from fastapi import BackgroundTasks

from backend.api.dependencies import get_providers
from backend.infrastructure.adapters.postgres_retail_analysis_state_adapter import (
    PostgresRetailAnalysisStateAdapter,
)
from backend.infrastructure.adapters.redis_analysis_event_stream_adapter import (
    RedisAnalysisEventStreamAdapter,
)
from backend.infrastructure.adapters.redis_analysis_job_queue_adapter import (
    RedisAnalysisJobQueueAdapter,
)


def test_default_api_dependency_uses_pg_redis_runtime_providers() -> None:
    first = get_providers(BackgroundTasks())
    second = get_providers(BackgroundTasks())

    assert isinstance(first.retail_analysis_state, PostgresRetailAnalysisStateAdapter)
    assert isinstance(first.analysis_job_queue, RedisAnalysisJobQueueAdapter)
    assert isinstance(first.analysis_event_stream, RedisAnalysisEventStreamAdapter)
    assert first.retail_analysis_state is second.retail_analysis_state
    assert first.analysis_job_queue is second.analysis_job_queue
    assert first.analysis_event_stream is second.analysis_event_stream
