"""Provider container assembly."""

from fastapi import BackgroundTasks

from backend.core.config import Settings
from backend.infrastructure.adapters.anthropic_llm_adapter import AnthropicLLMAdapter
from backend.infrastructure.adapters.console_telemetry_adapter import ConsoleTelemetryAdapter
from backend.infrastructure.adapters.csv_dataset_adapter import CsvDatasetAdapter
from backend.infrastructure.adapters.csv_retail_dataset_adapter import CsvRetailDatasetAdapter
from backend.infrastructure.adapters.edge_tts_speech_synthesis_adapter import (
    EdgeTtsSpeechSynthesisAdapter,
)
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
from backend.infrastructure.adapters.openai_compatible_llm_adapter import (
    OpenAICompatibleLLMAdapter,
)
from backend.providers.container import ProvidersContainer


def create_providers(
    settings: Settings,
    background_tasks: BackgroundTasks | None = None,
    llm_provider_name: str = "openai",
) -> ProvidersContainer:
    """Create the default local provider container from typed settings."""

    llm = AnthropicLLMAdapter() if llm_provider_name == "claude" else OpenAICompatibleLLMAdapter()

    return ProvidersContainer(
        repository=JsonProjectRepositoryAdapter("data"),
        storage=LocalProjectFileStorageAdapter("data"),
        assets=LocalGeneratedAssetAdapter(
            data_dir="data",
            outputs_dir=settings.OUTPUT_DIR,
            ai_audio_dir="backend/data/audio",
            temp_dir="/tmp",
        ),
        dataset=CsvDatasetAdapter("data"),
        retail_dataset=CsvRetailDatasetAdapter("data"),
        association_rules=LocalAssociationRuleStoreAdapter(),
        recommendation_models=LocalRecommendationModelStoreAdapter("backend/data/model_data.pkl"),
        analysis_artifacts=LocalAnalysisArtifactAdapter("data"),
        analysis_models=LocalAnalysisModelStoreAdapter("data"),
        speech=EdgeTtsSpeechSynthesisAdapter(),
        llm=llm,
        analysis_jobs=FastApiBackgroundAnalysisJobAdapter(background_tasks),
        telemetry=ConsoleTelemetryAdapter(),
    )
