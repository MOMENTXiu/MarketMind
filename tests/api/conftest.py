"""Shared API test fixtures: tmp_path-backed providers and helpers."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_providers
from backend.core.storage import ProjectStorage
from backend.infrastructure.adapters.console_telemetry_adapter import ConsoleTelemetryAdapter
from backend.infrastructure.adapters.csv_dataset_adapter import CsvDatasetAdapter
from backend.infrastructure.adapters.csv_retail_dataset_adapter import CsvRetailDatasetAdapter
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
from backend.infrastructure.adapters.local_regularized_dataset_adapter import (
    LocalRegularizedDatasetAdapter,
)
from backend.main import app
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisJobDTO
from tests.fakes.auth_providers import (
    FakeAuthTokenProvider,
    FakePasswordHasherProvider,
    FakeSseTicketProvider,
    FakeUserDirectoryProvider,
)
from tests.fakes.providers import (
    FakeLLMProvider,
    FakeRecommendationModelStoreProvider,
    FakeRegularizedDatasetProvider,
)


class RecordingAnalysisJobs:
    def __init__(self) -> None:
        self.jobs: list[AnalysisJobDTO] = []

    def submit_project_analysis(self, job: AnalysisJobDTO, handler: Any | None = None) -> None:
        self.jobs.append(job)


class SynchronousAnalysisJobs:
    """Executes the submitted handler synchronously for testing."""

    def submit_project_analysis(self, job: AnalysisJobDTO, handler: Any | None = None) -> None:
        if handler is not None:
            handler(job.project_id)


@dataclass
class IsolatedEnv:
    storage: ProjectStorage
    container: ProvidersContainer
    jobs: RecordingAnalysisJobs
    llm: FakeLLMProvider
    models: FakeRecommendationModelStoreProvider
    data_dir: Path
    outputs_dir: Path


@pytest.fixture()
def isolated_env(tmp_path: Path) -> Iterator[IsolatedEnv]:
    """Provide a tmp_path-backed ProvidersContainer and override get_providers."""

    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    storage = ProjectStorage(str(data_dir))
    jobs = RecordingAnalysisJobs()
    llm = FakeLLMProvider(text="generated broadcast")
    models = FakeRecommendationModelStoreProvider()
    container = ProvidersContainer(
        repository=JsonProjectRepositoryAdapter(str(data_dir)),
        storage=LocalProjectFileStorageAdapter(str(data_dir)),
        assets=LocalGeneratedAssetAdapter(
            data_dir=str(data_dir),
            outputs_dir=str(outputs_dir),
        ),
        dataset=CsvDatasetAdapter(str(data_dir)),
        retail_dataset=CsvRetailDatasetAdapter(str(data_dir)),
        association_rules=LocalAssociationRuleStoreAdapter(),
        recommendation_models=models,
        analysis_artifacts=LocalAnalysisArtifactAdapter(str(data_dir)),
        analysis_models=LocalAnalysisModelStoreAdapter(str(data_dir)),
        llm=llm,
        analysis_jobs=jobs,
        telemetry=ConsoleTelemetryAdapter(),
        regularized_dataset=FakeRegularizedDatasetProvider(),
        user_directory=FakeUserDirectoryProvider(),
        password_hasher=FakePasswordHasherProvider(),
        auth_token=FakeAuthTokenProvider(),
        sse_ticket=FakeSseTicketProvider(),
    )

    app.dependency_overrides[get_providers] = lambda: container
    try:
        yield IsolatedEnv(
            storage=storage,
            container=container,
            jobs=jobs,
            llm=llm,
            models=models,
            data_dir=data_dir,
            outputs_dir=outputs_dir,
        )
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def auth_client(isolated_env: IsolatedEnv) -> Iterator[tuple[TestClient, str, str]]:
    """Return a tuple of (client, access_token, user_id) for an authenticated test user."""
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    r = client.post("/api/auth/register", json={
        "email": "test-user@example.com",
        "password": "password123",
    })
    assert r.status_code == 201
    r = client.post("/api/auth/login", json={
        "email": "test-user@example.com",
        "password": "password123",
    })
    assert r.status_code == 200
    data = r.json()["data"]
    token = data["access_token"]
    user_id = data["user"]["id"]
    yield client, token, user_id


@pytest.fixture()
def isolated_env_real_adapter(tmp_path: Path) -> Iterator[IsolatedEnv]:
    """Variant using LocalRegularizedDatasetAdapter instead of Fake."""

    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    storage = ProjectStorage(str(data_dir))
    jobs = SynchronousAnalysisJobs()
    llm = FakeLLMProvider(text="generated broadcast")
    models = FakeRecommendationModelStoreProvider()
    container = ProvidersContainer(
        repository=JsonProjectRepositoryAdapter(str(data_dir)),
        storage=LocalProjectFileStorageAdapter(str(data_dir)),
        assets=LocalGeneratedAssetAdapter(
            data_dir=str(data_dir),
            outputs_dir=str(outputs_dir),
        ),
        dataset=CsvDatasetAdapter(str(data_dir)),
        retail_dataset=CsvRetailDatasetAdapter(str(data_dir)),
        association_rules=LocalAssociationRuleStoreAdapter(),
        recommendation_models=models,
        analysis_artifacts=LocalAnalysisArtifactAdapter(str(data_dir)),
        analysis_models=LocalAnalysisModelStoreAdapter(str(data_dir)),
        llm=llm,
        analysis_jobs=jobs,
        telemetry=ConsoleTelemetryAdapter(),
        regularized_dataset=LocalRegularizedDatasetAdapter(str(data_dir)),
        user_directory=FakeUserDirectoryProvider(),
        password_hasher=FakePasswordHasherProvider(),
        auth_token=FakeAuthTokenProvider(),
        sse_ticket=FakeSseTicketProvider(),
    )

    app.dependency_overrides[get_providers] = lambda: container
    try:
        yield IsolatedEnv(
            storage=storage,
            container=container,
            jobs=jobs,
            llm=llm,
            models=models,
            data_dir=data_dir,
            outputs_dir=outputs_dir,
        )
    finally:
        app.dependency_overrides.clear()
