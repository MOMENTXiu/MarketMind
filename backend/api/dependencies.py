"""FastAPI dependency providers wiring controllers to business pipelines/flows."""

from __future__ import annotations

from fastapi import BackgroundTasks, Depends

from backend.business.flows.project_analysis_flow import ProjectAnalysisFlow
from backend.business.pipelines.ai_voice_broadcast_pipeline import AIVoiceBroadcastPipeline
from backend.business.pipelines.association_analysis_pipeline import AssociationAnalysisPipeline
from backend.business.pipelines.dataset_upload_pipeline import DatasetUploadPipeline
from backend.business.pipelines.project_pipeline import ProjectPipeline
from backend.business.pipelines.project_read_pipelines import (
    ProjectCustomerPipeline,
    ProjectRecommendationPipeline,
)
from backend.business.pipelines.recommendation_pipeline import RecommendationPipeline
from backend.business.pipelines.voice_synthesis_pipeline import VoiceSynthesisPipeline
from backend.core.config import settings
from backend.infrastructure.factories.provider_factory import create_providers
from backend.providers.container import ProvidersContainer


def get_providers(background_tasks: BackgroundTasks) -> ProvidersContainer:
    """Build a per-request providers container bound to this request's BackgroundTasks."""

    return create_providers(settings, background_tasks=background_tasks)


def get_project_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> ProjectPipeline:
    return ProjectPipeline(providers)


def get_dataset_upload_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> DatasetUploadPipeline:
    return DatasetUploadPipeline(providers)


def get_project_customer_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> ProjectCustomerPipeline:
    return ProjectCustomerPipeline(providers)


def get_project_recommendation_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> ProjectRecommendationPipeline:
    return ProjectRecommendationPipeline(providers)


def get_recommendation_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> RecommendationPipeline:
    return RecommendationPipeline(providers)


def get_association_analysis_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> AssociationAnalysisPipeline:
    return AssociationAnalysisPipeline(providers)


def get_voice_synthesis_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> VoiceSynthesisPipeline:
    return VoiceSynthesisPipeline(providers)


def get_ai_voice_broadcast_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> AIVoiceBroadcastPipeline:
    return AIVoiceBroadcastPipeline(providers)


def get_project_analysis_flow(
    providers: ProvidersContainer = Depends(get_providers),
) -> ProjectAnalysisFlow:
    return ProjectAnalysisFlow(providers)
