"""JSON-backed project repository adapter."""

from backend.core.storage import ProjectStorage
from backend.models.project import (
    AnalysisParameters,
    AnalysisResults,
    Project,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
)


class JsonProjectRepositoryAdapter:
    """Project repository provider backed by the existing JSON storage behavior."""

    def __init__(self, data_dir: str = "data") -> None:
        self._storage = ProjectStorage(data_dir)

    def create_project(self, project_data: ProjectCreate) -> Project:
        project = Project(
            name=project_data.name,
            description=project_data.description,
            parameters=project_data.parameters or AnalysisParameters(),
        )
        return self._storage.create_project(project)

    def get_project(self, project_id: str, owner_user_id: str | None = None) -> Project | None:
        project = self._storage.get_project(project_id)
        if project is None:
            return None
        if owner_user_id is not None and project.owner_user_id != owner_user_id:
            return None
        return project

    def list_projects(self, skip: int = 0, limit: int = 100, owner_user_id: str | None = None) -> list[Project]:
        projects = self._storage.list_projects(skip=skip, limit=limit)
        if owner_user_id is not None:
            projects = [p for p in projects if p.owner_user_id == owner_user_id]
        return projects

    def update_project(self, project_id: str, update_data: ProjectUpdate) -> Project | None:
        return self._storage.update_project(project_id, update_data.model_dump(exclude_none=True))

    def mark_analysis_completed(self, project_id: str, results: AnalysisResults) -> Project | None:
        return self._storage.update_project(
            project_id,
            {
                "status": ProjectStatus.COMPLETED,
                "results": results.model_dump(),
                "error_message": None,
            },
        )

    def mark_analysis_failed(self, project_id: str, error_message: str) -> Project | None:
        return self._storage.update_project(
            project_id,
            {
                "status": ProjectStatus.FAILED,
                "error_message": error_message,
            },
        )

    def delete_project(self, project_id: str, owner_user_id: str | None = None) -> bool:
        if owner_user_id is not None:
            project = self.get_project(project_id, owner_user_id=owner_user_id)
            if project is None:
                return False
        return self._storage.delete_project(project_id)

    def count_projects(self, owner_user_id: str | None = None) -> int:
        if owner_user_id is not None:
            return len(self.list_projects(owner_user_id=owner_user_id))
        return self._storage.count_projects()
