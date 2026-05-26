"""FastAPI dependency providers wiring controllers to business pipelines/flows."""

from __future__ import annotations

from fastapi import BackgroundTasks, Depends

from backend.business.flows.data_processing_analysis_flow import DataProcessingAnalysisFlow
from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow
from backend.business.pipelines.ai_voice_broadcast_pipeline import AIVoiceBroadcastPipeline
from backend.business.pipelines.voice_synthesis_pipeline import VoiceSynthesisPipeline
from backend.core.config import settings
from backend.infrastructure.factories.provider_factory import create_providers
from backend.providers.container import ProvidersContainer


def get_providers(background_tasks: BackgroundTasks) -> ProvidersContainer:
    """Build a per-request providers container bound to this request's BackgroundTasks."""

    return create_providers(settings, background_tasks=background_tasks)


def get_voice_synthesis_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> VoiceSynthesisPipeline:
    return VoiceSynthesisPipeline(providers)


def get_ai_voice_broadcast_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> AIVoiceBroadcastPipeline:
    return AIVoiceBroadcastPipeline(providers)


def get_retail_analysis_flow(
    providers: ProvidersContainer = Depends(get_providers),
) -> RetailAnalysisFlow:
    return RetailAnalysisFlow(providers)


def get_data_processing_analysis_flow(
    providers: ProvidersContainer = Depends(get_providers),
) -> DataProcessingAnalysisFlow:
    return DataProcessingAnalysisFlow(providers)
