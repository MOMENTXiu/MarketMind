"""Typed provider container used by future business layers."""

from dataclasses import dataclass, field

from backend.providers.admin_user_provider import AdminUserProvider
from backend.providers.alert_provider import AlertProvider
from backend.providers.analysis_artifact_provider import AnalysisArtifactProvider
from backend.providers.analysis_event_stream_provider import (
    AnalysisEventStreamProvider,
    InMemoryAnalysisEventStreamProvider,
)
from backend.providers.analysis_job_provider import AnalysisJobProvider
from backend.providers.analysis_job_queue_provider import (
    AnalysisJobQueueProvider,
    InMemoryAnalysisJobQueueProvider,
)
from backend.providers.analysis_model_store_provider import AnalysisModelStoreProvider
from backend.providers.association_rule_store_provider import AssociationRuleStoreProvider
from backend.providers.auth_token_provider import AuthTokenProvider
from backend.providers.dataset_provider import DatasetProvider
from backend.providers.env_file_provider import EnvFileProvider
from backend.providers.generated_asset_provider import GeneratedAssetProvider
from backend.providers.infrastructure_health_provider import InfrastructureHealthProvider
from backend.providers.llm_provider import LLMProvider
from backend.providers.log_query_provider import LogQueryProvider
from backend.providers.password_hasher_provider import PasswordHasherProvider
from backend.providers.project_file_storage_provider import ProjectFileStorageProvider
from backend.providers.project_repository_provider import ProjectRepositoryProvider
from backend.providers.recommendation_model_store_provider import RecommendationModelStoreProvider
from backend.providers.regularized_dataset_provider import RegularizedDatasetProvider
from backend.providers.retail_analysis_state_provider import (
    InMemoryRetailAnalysisStateProvider,
    RetailAnalysisStateProvider,
)
from backend.providers.retail_dataset_provider import RetailDatasetProvider
from backend.providers.settings_inspection_provider import SettingsInspectionProvider
from backend.providers.sse_ticket_provider import SseTicketProvider
from backend.providers.telemetry_provider import TelemetryProvider
from backend.providers.user_directory_provider import UserDirectoryProvider


@dataclass(frozen=True)
class ProvidersContainer:
    repository: ProjectRepositoryProvider
    storage: ProjectFileStorageProvider
    assets: GeneratedAssetProvider
    dataset: DatasetProvider
    retail_dataset: RetailDatasetProvider
    regularized_dataset: RegularizedDatasetProvider
    association_rules: AssociationRuleStoreProvider
    recommendation_models: RecommendationModelStoreProvider
    analysis_artifacts: AnalysisArtifactProvider
    analysis_models: AnalysisModelStoreProvider
    llm: LLMProvider
    analysis_jobs: AnalysisJobProvider
    telemetry: TelemetryProvider
    retail_analysis_state: RetailAnalysisStateProvider = field(
        default_factory=InMemoryRetailAnalysisStateProvider
    )
    analysis_job_queue: AnalysisJobQueueProvider = field(
        default_factory=InMemoryAnalysisJobQueueProvider
    )
    analysis_event_stream: AnalysisEventStreamProvider = field(
        default_factory=InMemoryAnalysisEventStreamProvider
    )
    user_directory: UserDirectoryProvider | None = None
    password_hasher: PasswordHasherProvider | None = None
    auth_token: AuthTokenProvider | None = None
    sse_ticket: SseTicketProvider | None = None
    health: InfrastructureHealthProvider | None = None
    settings_inspection: SettingsInspectionProvider | None = None
    alert: AlertProvider | None = None
    log_query: LogQueryProvider | None = None
    admin_users: AdminUserProvider | None = None
    env_file: EnvFileProvider | None = None
