"""JSON-backed project repository adapter."""

from backend.core.storage import ProjectStorage
from backend.models.project import AnalysisParameters, Project, ProjectCreate, ProjectUpdate


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

    def get_project(self, project_id: str) -> Project | None:
        return self._storage.get_project(project_id)

    def list_projects(self, skip: int = 0, limit: int = 100) -> list[Project]:
        return self._storage.list_projects(skip=skip, limit=limit)

    def update_project(self, project_id: str, update_data: ProjectUpdate) -> Project | None:
        return self._storage.update_project(project_id, update_data.model_dump(exclude_none=True))

    def delete_project(self, project_id: str) -> bool:
        return self._storage.delete_project(project_id)

    def count_projects(self) -> int:
        return self._storage.count_projects()
