"""Contract tests for the JSON project repository adapter."""

from __future__ import annotations

from datetime import timedelta

from backend.infrastructure.adapters.json_project_repository_adapter import (
    JsonProjectRepositoryAdapter,
)
from backend.models.project import AnalysisParameters, ProjectCreate, ProjectUpdate


def test_json_project_repository_crud_preserves_current_storage_behavior(tmp_path) -> None:
    adapter = JsonProjectRepositoryAdapter(str(tmp_path / "data"))

    first = adapter.create_project(ProjectCreate(name="First"))
    second = adapter.create_project(
        ProjectCreate(
            name="Second",
            description="with params",
            parameters=AnalysisParameters(min_support=0.05),
        )
    )

    assert adapter.count_projects() == 2
    assert adapter.get_project(first.id) is not None
    assert adapter.get_project(second.id).parameters.min_support == 0.05
    assert (tmp_path / "data/projects" / first.id / "outputs/charts").exists()
    assert (tmp_path / "data/projects" / first.id / "outputs/reports").exists()
    assert (tmp_path / "data/projects" / first.id / "outputs/audio").exists()

    first.created_at = second.created_at + timedelta(seconds=1)
    adapter._storage.update_project(first.id, {"created_at": first.created_at})
    projects = adapter.list_projects()
    assert [project.id for project in projects] == [first.id, second.id]
    assert [project.id for project in adapter.list_projects(skip=1, limit=1)] == [second.id]

    updated = adapter.update_project(first.id, ProjectUpdate(name="First Updated"))
    assert updated is not None
    assert updated.name == "First Updated"
    assert adapter.get_project(first.id).name == "First Updated"

    assert adapter.delete_project(second.id) is True
    assert adapter.get_project(second.id) is None
    assert adapter.count_projects() == 1
    assert not (tmp_path / "data/projects" / second.id).exists()


def test_json_project_repository_missing_operations_return_current_values(tmp_path) -> None:
    adapter = JsonProjectRepositoryAdapter(str(tmp_path / "data"))

    assert adapter.get_project("missing") is None
    assert adapter.update_project("missing", ProjectUpdate(name="Nope")) is None
    assert adapter.delete_project("missing") is False
