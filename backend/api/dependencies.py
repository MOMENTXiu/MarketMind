"""FastAPI dependency providers wiring controllers to business pipelines/flows."""

from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks, Depends

from backend.business.flows.data_processing_analysis_flow import DataProcessingAnalysisFlow
from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow
from backend.business.pipelines.customer_text_suggestion_pipeline import (
    CustomerTextSuggestionPipeline,
)
from backend.core.config import Settings as _Settings
from backend.core.config import settings
from backend.infrastructure.factories.provider_factory import create_providers
from backend.providers.container import ProvidersContainer


def get_providers(background_tasks: BackgroundTasks) -> ProvidersContainer:
    """Build a per-request providers container bound to this request's BackgroundTasks."""

    return create_providers(settings, background_tasks=background_tasks)


def get_customer_text_suggestion_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> CustomerTextSuggestionPipeline:
    return CustomerTextSuggestionPipeline(providers)


def get_retail_analysis_flow(
    providers: ProvidersContainer = Depends(get_providers),
) -> RetailAnalysisFlow:
    return RetailAnalysisFlow(providers)


def get_data_processing_analysis_flow(
    providers: ProvidersContainer = Depends(get_providers),
) -> DataProcessingAnalysisFlow:
    return DataProcessingAnalysisFlow(providers)


def get_settings() -> _Settings:
    """Return the global settings instance (safe for API layer)."""
    return settings


def get_minio_storage(settings: _Settings) -> Any:
    """Create a MinIO storage adapter if backend is minio."""
    if settings.OBJECT_STORAGE_BACKEND == "minio":
        from backend.infrastructure.adapters.minio_object_storage_adapter import (
            MinioObjectStorageAdapter,
        )

        return MinioObjectStorageAdapter(
            endpoint=settings.OBJECT_STORAGE_ENDPOINT,
            access_key=settings.OBJECT_STORAGE_ACCESS_KEY,
            secret_key=settings.OBJECT_STORAGE_SECRET_KEY,
            bucket=settings.OBJECT_STORAGE_BUCKET,
            region=settings.OBJECT_STORAGE_REGION,
            secure=settings.OBJECT_STORAGE_SECURE,
        )
    return None
