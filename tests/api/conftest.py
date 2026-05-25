"""Shared API test fixtures: tmp_path-backed providers and helpers."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from backend.api.dependencies import get_providers
from backend.core.storage import ProjectStorage
from backend.infrastructure.adapters.console_telemetry_adapter import ConsoleTelemetryAdapter
from backend.infrastructure.adapters.csv_dataset_adapter import CsvDatasetAdapter
from backend.infrastructure.adapters.json_project_repository_adapter import (
    JsonProjectRepositoryAdapter,
)
from backend.infrastructure.adapters.local_association_rule_store_adapter import (
    LocalAssociationRuleStoreAdapter,
)
from backend.infrastructure.adapters.local_generated_asset_adapter import LocalGeneratedAssetAdapter
from backend.infrastructure.adapters.local_project_file_storage_adapter import (
    LocalProjectFileStorageAdapter,
)
from backend.main import app
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisJobDTO
from tests.fakes.providers import (
    FakeLLMProvider,
    FakeRecommendationModelStoreProvider,
    FakeSpeechSynthesisProvider,
)


class RecordingAnalysisJobs:
    def __init__(self) -> None:
        self.jobs: list[AnalysisJobDTO] = []

    def submit_project_analysis(self, job: AnalysisJobDTO, handler: Any | None = None) -> None:
        self.jobs.append(job)


@dataclass
class IsolatedEnv:
    storage: ProjectStorage
    container: ProvidersContainer
    jobs: RecordingAnalysisJobs
    speech: FakeSpeechSynthesisProvider
    llm: FakeLLMProvider
    models: FakeRecommendationModelStoreProvider
    data_dir: Path
    outputs_dir: Path
    ai_audio_dir: Path


@pytest.fixture()
def isolated_env(tmp_path: Path) -> Iterator[IsolatedEnv]:
    """Provide a tmp_path-backed ProvidersContainer and override get_providers."""

    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    ai_audio_dir = tmp_path / "ai_audio"
    data_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    ai_audio_dir.mkdir(parents=True, exist_ok=True)

    storage = ProjectStorage(str(data_dir))
    jobs = RecordingAnalysisJobs()
    speech = FakeSpeechSynthesisProvider()
    llm = FakeLLMProvider(text="generated broadcast")
    models = FakeRecommendationModelStoreProvider()
    container = ProvidersContainer(
        repository=JsonProjectRepositoryAdapter(str(data_dir)),
        storage=LocalProjectFileStorageAdapter(str(data_dir)),
        assets=LocalGeneratedAssetAdapter(
            data_dir=str(data_dir),
            outputs_dir=str(outputs_dir),
            ai_audio_dir=str(ai_audio_dir),
            temp_dir="/tmp",
        ),
        dataset=CsvDatasetAdapter(str(data_dir)),
        association_rules=LocalAssociationRuleStoreAdapter(),
        recommendation_models=models,
        speech=speech,
        llm=llm,
        analysis_jobs=jobs,
        telemetry=ConsoleTelemetryAdapter(),
    )

    app.dependency_overrides[get_providers] = lambda: container
    try:
        yield IsolatedEnv(
            storage=storage,
            container=container,
            jobs=jobs,
            speech=speech,
            llm=llm,
            models=models,
            data_dir=data_dir,
            outputs_dir=outputs_dir,
            ai_audio_dir=ai_audio_dir,
        )
    finally:
        app.dependency_overrides.clear()
