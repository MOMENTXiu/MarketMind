"""Provider container assembly."""

from functools import lru_cache
from typing import Any

from fastapi import BackgroundTasks

from backend.core.config import Settings
from backend.core.errors import InfrastructureError
from backend.infrastructure.adapters.anthropic_llm_adapter import AnthropicLLMAdapter
from backend.infrastructure.adapters.console_telemetry_adapter import ConsoleTelemetryAdapter
from backend.infrastructure.adapters.csv_dataset_adapter import CsvDatasetAdapter
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
from backend.infrastructure.adapters.local_association_rule_store_adapter import (
    LocalAssociationRuleStoreAdapter,
)
from backend.infrastructure.adapters.local_generated_asset_adapter import LocalGeneratedAssetAdapter
from backend.infrastructure.adapters.local_project_file_storage_adapter import (
    LocalProjectFileStorageAdapter,
)
from backend.infrastructure.adapters.local_recommendation_model_store_adapter import (
    LocalRecommendationModelStoreAdapter,
)
from backend.infrastructure.adapters.local_regularized_dataset_adapter import (
    LocalRegularizedDatasetAdapter,
)
from backend.infrastructure.adapters.minio_analysis_artifact_adapter import (
    MinioAnalysisArtifactAdapter,
)
from backend.infrastructure.adapters.minio_analysis_model_store_adapter import (
    MinioAnalysisModelStoreAdapter,
)
from backend.infrastructure.adapters.minio_object_storage_adapter import (
    MinioObjectStorageAdapter,
)
from backend.infrastructure.adapters.minio_regularized_dataset_adapter import (
    MinioRegularizedDatasetAdapter,
)
from backend.infrastructure.adapters.openai_compatible_llm_adapter import (
    OpenAICompatibleLLMAdapter,
)
from backend.infrastructure.adapters.redis_analysis_event_stream_adapter import (
    RedisAnalysisEventStreamAdapter,
)
from backend.infrastructure.adapters.redis_analysis_job_queue_adapter import (
    RedisAnalysisJobQueueAdapter,
)
from backend.providers.analysis_event_stream_provider import InMemoryAnalysisEventStreamProvider
from backend.providers.analysis_job_queue_provider import InMemoryAnalysisJobQueueProvider
from backend.providers.container import ProvidersContainer
from backend.providers.retail_analysis_state_provider import InMemoryRetailAnalysisStateProvider


def create_providers(
    settings: Settings,
    background_tasks: BackgroundTasks | None = None,
    llm_provider_name: str = "openai",
) -> ProvidersContainer:
    """Create the default local provider container from typed settings."""

    llm = AnthropicLLMAdapter() if llm_provider_name == "claude" else OpenAICompatibleLLMAdapter()

    retail_analysis_state = InMemoryRetailAnalysisStateProvider()
    analysis_job_queue = InMemoryAnalysisJobQueueProvider()
    analysis_event_stream = InMemoryAnalysisEventStreamProvider()
    if settings.TASK_QUEUE_BACKEND == "redis":
        retail_analysis_state, analysis_job_queue, analysis_event_stream = (
            _build_phase3_redis_providers(settings)
        )

    if settings.OBJECT_STORAGE_BACKEND == "minio":
        minio_storage = _build_minio_storage(settings)
        regularized_dataset = MinioRegularizedDatasetAdapter(minio_storage)
        analysis_artifacts = MinioAnalysisArtifactAdapter(minio_storage)
        analysis_models = MinioAnalysisModelStoreAdapter(minio_storage)
    else:
        regularized_dataset = LocalRegularizedDatasetAdapter("data")
        analysis_artifacts = LocalAnalysisArtifactAdapter("data")
        analysis_models = LocalAnalysisModelStoreAdapter("data")

    return ProvidersContainer(
        repository=JsonProjectRepositoryAdapter("data"),
        storage=LocalProjectFileStorageAdapter("data"),
        assets=LocalGeneratedAssetAdapter(
            data_dir="data",
            outputs_dir=settings.OUTPUT_DIR,
        ),
        dataset=CsvDatasetAdapter("data"),
        retail_dataset=CsvRetailDatasetAdapter("data"),
        regularized_dataset=regularized_dataset,
        association_rules=LocalAssociationRuleStoreAdapter(),
        recommendation_models=LocalRecommendationModelStoreAdapter("backend/data/model_data.pkl"),
        analysis_artifacts=analysis_artifacts,
        analysis_models=analysis_models,
        llm=llm,
        analysis_jobs=FastApiBackgroundAnalysisJobAdapter(background_tasks),
        telemetry=ConsoleTelemetryAdapter(),
        retail_analysis_state=retail_analysis_state,
        analysis_job_queue=analysis_job_queue,
        analysis_event_stream=analysis_event_stream,
    )


def _build_phase3_redis_providers(
    settings: Settings,
) -> tuple[Any, Any, Any]:
    if not settings.REDIS_ENABLED:
        raise InfrastructureError(
            "TASK_QUEUE_BACKEND=redis requires REDIS_ENABLED=true for provider assembly"
        )

    return _build_phase3_redis_providers_cached(
        settings.DATABASE_URL,
        settings.DB_ECHO,
        settings.DB_POOL_SIZE,
        settings.DB_POOL_MAX_OVERFLOW,
        settings.REDIS_URL,
        settings.ANALYSIS_QUEUE_NAME,
        settings.ANALYSIS_EVENT_HEARTBEAT_MS,
        settings.ANALYSIS_EVENT_RETRY_MS,
    )


def _build_minio_storage(settings: Settings) -> MinioObjectStorageAdapter:
    return MinioObjectStorageAdapter(
        endpoint=settings.OBJECT_STORAGE_ENDPOINT,
        access_key=settings.OBJECT_STORAGE_ACCESS_KEY,
        secret_key=settings.OBJECT_STORAGE_SECRET_KEY,
        bucket=settings.OBJECT_STORAGE_BUCKET,
        region=settings.OBJECT_STORAGE_REGION,
        secure=settings.OBJECT_STORAGE_SECURE,
        presigned_ttl_seconds=settings.OBJECT_STORAGE_PRESIGNED_URL_TTL_SECONDS,
        public_endpoint=settings.OBJECT_STORAGE_PUBLIC_ENDPOINT,
    )


@lru_cache(maxsize=8)
def _build_phase3_redis_providers_cached(
    database_url: str,
    db_echo: bool,
    db_pool_size: int,
    db_pool_max_overflow: int,
    redis_url: str,
    queue_name: str,
    heartbeat_ms: int,
    retry_ms: int,
) -> tuple[Any, Any, Any]:
    from redis import Redis
    from rq import Queue

    from backend.infrastructure.adapters.postgres_retail_analysis_state_adapter import (
        PostgresRetailAnalysisStateAdapter,
    )
    from backend.infrastructure.db.session import create_db_engine, create_session_factory

    runtime_settings = Settings(
        _env_file=None,
        DATABASE_URL=database_url,
        DB_ECHO=db_echo,
        DB_POOL_SIZE=db_pool_size,
        DB_POOL_MAX_OVERFLOW=db_pool_max_overflow,
        REDIS_URL=redis_url,
        ANALYSIS_QUEUE_NAME=queue_name,
        ANALYSIS_EVENT_HEARTBEAT_MS=heartbeat_ms,
        ANALYSIS_EVENT_RETRY_MS=retry_ms,
        REDIS_ENABLED=True,
        TASK_QUEUE_BACKEND="redis",
    )
    engine = create_db_engine(runtime_settings)
    session_factory = create_session_factory(engine)
    redis_client = Redis.from_url(redis_url, decode_responses=True)
    queue = Queue(queue_name, connection=redis_client)
    return (
        PostgresRetailAnalysisStateAdapter(session_factory),
        RedisAnalysisJobQueueAdapter(queue),
        RedisAnalysisEventStreamAdapter(
            redis_client,
            heartbeat_interval_ms=heartbeat_ms,
            retry_ms=retry_ms,
        ),
    )
