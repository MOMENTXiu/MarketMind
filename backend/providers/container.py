"""Typed provider container used by future business layers."""

from dataclasses import dataclass

from backend.providers.analysis_job_provider import AnalysisJobProvider
from backend.providers.association_rule_store_provider import AssociationRuleStoreProvider
from backend.providers.dataset_provider import DatasetProvider
from backend.providers.generated_asset_provider import GeneratedAssetProvider
from backend.providers.llm_provider import LLMProvider
from backend.providers.project_file_storage_provider import ProjectFileStorageProvider
from backend.providers.project_repository_provider import ProjectRepositoryProvider
from backend.providers.recommendation_model_store_provider import RecommendationModelStoreProvider
from backend.providers.speech_synthesis_provider import SpeechSynthesisProvider
from backend.providers.telemetry_provider import TelemetryProvider


@dataclass(frozen=True)
class ProvidersContainer:
    repository: ProjectRepositoryProvider
    storage: ProjectFileStorageProvider
    assets: GeneratedAssetProvider
    dataset: DatasetProvider
    association_rules: AssociationRuleStoreProvider
    recommendation_models: RecommendationModelStoreProvider
    speech: SpeechSynthesisProvider
    llm: LLMProvider
    analysis_jobs: AnalysisJobProvider
    telemetry: TelemetryProvider
