"""Project metadata repository provider interface."""

from typing import Protocol

from backend.models.project import Project, ProjectCreate, ProjectUpdate


class ProjectRepositoryProvider(Protocol):
    def create_project(self, project_data: ProjectCreate) -> Project:
        """Create and persist a project."""

    def get_project(self, project_id: str) -> Project | None:
        """Return one project by id."""

    def list_projects(self, skip: int = 0, limit: int = 100) -> list[Project]:
        """Return projects sorted using current storage semantics."""

    def update_project(self, project_id: str, update_data: ProjectUpdate) -> Project | None:
        """Update a project and return the persisted result."""

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and its metadata."""

    def count_projects(self) -> int:
        """Return the total number of projects."""
