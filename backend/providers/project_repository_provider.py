"""Project metadata repository provider interface."""

from typing import Protocol

from backend.models.project import AnalysisResults, Project, ProjectCreate, ProjectUpdate


class ProjectRepositoryProvider(Protocol):
    def create_project(self, project_data: ProjectCreate) -> Project:
        """Create and persist a project."""

    def get_project(self, project_id: str, owner_user_id: str | None = None) -> Project | None:
        """Return one project by id, optionally scoped to an owner."""

    def list_projects(
        self, skip: int = 0, limit: int = 100, owner_user_id: str | None = None
    ) -> list[Project]:
        """Return projects sorted using current storage semantics, optionally scoped to an owner."""

    def update_project(self, project_id: str, update_data: ProjectUpdate) -> Project | None:
        """Update a project and return the persisted result."""

    def mark_analysis_completed(self, project_id: str, results: AnalysisResults) -> Project | None:
        """Persist successful analysis outcome (status=已完成, results, clear error_message)."""

    def mark_analysis_failed(self, project_id: str, error_message: str) -> Project | None:
        """Persist failed analysis outcome (status=失败, error_message)."""

    def delete_project(self, project_id: str, owner_user_id: str | None = None) -> bool:
        """Delete a project and its metadata, optionally scoped to an owner."""

    def count_projects(self, owner_user_id: str | None = None) -> int:
        """Return the total number of projects, optionally scoped to an owner."""
