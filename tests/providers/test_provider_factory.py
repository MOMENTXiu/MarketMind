"""Contract tests for provider factory assembly."""

from __future__ import annotations

import pytest
from fastapi import BackgroundTasks

from backend.core.config import Settings
from backend.core.errors import InfrastructureError
from backend.infrastructure.adapters.anthropic_llm_adapter import AnthropicLLMAdapter
from backend.infrastructure.adapters.console_telemetry_adapter import ConsoleTelemetryAdapter
from backend.infrastructure.adapters.csv_retail_dataset_adapter import CsvRetailDatasetAdapter
from backend.infrastructure.adapters.fastapi_background_analysis_job_adapter import (
    FastApiBackgroundAnalysisJobAdapter,
)
from backend.infrastructure.adapters.json_project_repository_adapter import (
    JsonProjectRepositoryAdapter,
)
from backend.infrastructure.adapters.local_analysis_artifact_adapter import (
    LocalAnalysisArtifactAdapter,
)
from backend.infrastructure.adapters.local_analysis_model_store_adapter import (
    LocalAnalysisModelStoreAdapter,
)
from backend.infrastructure.adapters.openai_compatible_llm_adapter import (
    OpenAICompatibleLLMAdapter,
)
from backend.infrastructure.adapters.postgres_retail_analysis_state_adapter import (
    PostgresRetailAnalysisStateAdapter,
)
from backend.infrastructure.adapters.redis_analysis_event_stream_adapter import (
    RedisAnalysisEventStreamAdapter,
)
from backend.infrastructure.adapters.redis_analysis_job_queue_adapter import (
    RedisAnalysisJobQueueAdapter,
)
from backend.infrastructure.factories.provider_factory import create_providers
from backend.providers.analysis_event_stream_provider import InMemoryAnalysisEventStreamProvider
from backend.providers.analysis_job_queue_provider import InMemoryAnalysisJobQueueProvider
from backend.providers.dtos import AnalysisJobDTO
from backend.providers.retail_analysis_state_provider import InMemoryRetailAnalysisStateProvider


def test_provider_factory_creates_default_pg_redis_runtime_container() -> None:
    providers = create_providers(Settings(_env_file=None))

    assert isinstance(providers.repository, JsonProjectRepositoryAdapter)
    assert isinstance(providers.llm, OpenAICompatibleLLMAdapter)
    assert isinstance(providers.analysis_jobs, FastApiBackgroundAnalysisJobAdapter)
    assert isinstance(providers.telemetry, ConsoleTelemetryAdapter)
    assert isinstance(providers.retail_dataset, CsvRetailDatasetAdapter)
    assert isinstance(providers.analysis_artifacts, LocalAnalysisArtifactAdapter)
    assert isinstance(providers.analysis_models, LocalAnalysisModelStoreAdapter)
    assert isinstance(providers.retail_analysis_state, PostgresRetailAnalysisStateAdapter)
    assert isinstance(providers.analysis_job_queue, RedisAnalysisJobQueueAdapter)
    assert isinstance(providers.analysis_event_stream, RedisAnalysisEventStreamAdapter)


def test_provider_factory_can_create_explicit_local_test_container() -> None:
    providers = create_providers(
        Settings(_env_file=None, TASK_QUEUE_BACKEND="none", REDIS_ENABLED=False)
    )

    assert isinstance(providers.retail_analysis_state, InMemoryRetailAnalysisStateProvider)
    assert isinstance(providers.analysis_job_queue, InMemoryAnalysisJobQueueProvider)
    assert isinstance(providers.analysis_event_stream, InMemoryAnalysisEventStreamProvider)


def test_provider_factory_can_select_anthropic_llm() -> None:
    providers = create_providers(Settings(_env_file=None), llm_provider_name="claude")

    assert isinstance(providers.llm, AnthropicLLMAdapter)


def test_provider_factory_can_select_phase3_redis_backends() -> None:
    providers = create_providers(
        Settings(
            _env_file=None,
            TASK_QUEUE_BACKEND="redis",
            REDIS_ENABLED=True,
            DATABASE_URL="sqlite+pysqlite:///:memory:",
            REDIS_URL="redis://localhost:6379/9",
        )
    )

    assert isinstance(providers.retail_analysis_state, PostgresRetailAnalysisStateAdapter)
    assert isinstance(providers.analysis_job_queue, RedisAnalysisJobQueueAdapter)
    assert isinstance(providers.analysis_event_stream, RedisAnalysisEventStreamAdapter)


def test_provider_factory_reuses_phase3_redis_runtime_resources() -> None:
    settings = Settings(
        _env_file=None,
        TASK_QUEUE_BACKEND="redis",
        REDIS_ENABLED=True,
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/9",
    )

    first = create_providers(settings)
    second = create_providers(settings)

    assert first.retail_analysis_state is second.retail_analysis_state
    assert first.analysis_job_queue is second.analysis_job_queue
    assert first.analysis_event_stream is second.analysis_event_stream


def test_provider_factory_requires_redis_enabled_for_redis_backend() -> None:
    with pytest.raises(InfrastructureError):
        create_providers(
            Settings(
                _env_file=None,
                TASK_QUEUE_BACKEND="redis",
                REDIS_ENABLED=False,
                DATABASE_URL="sqlite+pysqlite:///:memory:",
                REDIS_URL="redis://localhost:6379/9",
            )
        )


def test_fastapi_background_analysis_job_adapter_schedules_background_task() -> None:
    calls: list[str] = []

    def handler(project_id: str) -> None:
        calls.append(project_id)

    background_tasks = BackgroundTasks()
    adapter = FastApiBackgroundAnalysisJobAdapter(background_tasks)
    adapter.submit_project_analysis(AnalysisJobDTO(project_id="project-1", trigger="test"), handler)

    assert len(background_tasks.tasks) == 1
    background_tasks.tasks[0].func(*background_tasks.tasks[0].args)
    assert calls == ["project-1"]


def test_fastapi_background_analysis_job_adapter_runs_sync_handler_without_background() -> None:
    calls: list[str] = []
    adapter = FastApiBackgroundAnalysisJobAdapter()

    adapter.submit_project_analysis(
        AnalysisJobDTO(project_id="project-2", trigger="test"),
        lambda project_id: calls.append(project_id),
    )

    assert calls == ["project-2"]
