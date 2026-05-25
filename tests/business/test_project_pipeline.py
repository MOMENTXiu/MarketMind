"""Pipeline contract tests for ProjectPipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.business.pipelines.project_pipeline import ProjectPipeline
from backend.core.errors import NotFoundError
from backend.models.project import ProjectCreate, ProjectUpdate
from backend.providers.container import ProvidersContainer
from tests.fakes.providers import (
    FakeAnalysisJobProvider,
    FakeAssociationRuleStoreProvider,
    FakeDatasetProvider,
    FakeGeneratedAssetProvider,
    FakeLLMProvider,
    FakeProjectFileStorageProvider,
    FakeProjectRepositoryProvider,
    FakeRecommendationModelStoreProvider,
    FakeSpeechSynthesisProvider,
    FakeTelemetryProvider,
)


def _make_container(tmp_path: Path) -> ProvidersContainer:
    return ProvidersContainer(
        repository=FakeProjectRepositoryProvider(),
        storage=FakeProjectFileStorageProvider(tmp_path / "projects"),
        assets=FakeGeneratedAssetProvider(tmp_path / "assets"),
        dataset=FakeDatasetProvider(),
        association_rules=FakeAssociationRuleStoreProvider(),
        recommendation_models=FakeRecommendationModelStoreProvider(),
        speech=FakeSpeechSynthesisProvider(),
        llm=FakeLLMProvider(),
        analysis_jobs=FakeAnalysisJobProvider(),
        telemetry=FakeTelemetryProvider(),
    )


def test_create_then_get_returns_same_project(tmp_path: Path) -> None:
    pipeline = ProjectPipeline(_make_container(tmp_path))
    created = pipeline.create(ProjectCreate(name="demo"))
    fetched = pipeline.get(created.id)
    assert fetched.id == created.id
    assert fetched.name == "demo"


def test_list_returns_items_and_total(tmp_path: Path) -> None:
    pipeline = ProjectPipeline(_make_container(tmp_path))
    pipeline.create(ProjectCreate(name="a"))
    pipeline.create(ProjectCreate(name="b"))
    items, total = pipeline.list()
    assert total == 2
    assert {p.name for p in items} == {"a", "b"}


def test_update_changes_fields(tmp_path: Path) -> None:
    pipeline = ProjectPipeline(_make_container(tmp_path))
    created = pipeline.create(ProjectCreate(name="demo"))
    updated = pipeline.update(created.id, ProjectUpdate(description="new"))
    assert updated.description == "new"


def test_get_missing_raises_not_found(tmp_path: Path) -> None:
    pipeline = ProjectPipeline(_make_container(tmp_path))
    with pytest.raises(NotFoundError):
        pipeline.get("missing-id")


def test_delete_missing_raises_not_found(tmp_path: Path) -> None:
    pipeline = ProjectPipeline(_make_container(tmp_path))
    with pytest.raises(NotFoundError):
        pipeline.delete("missing-id")
