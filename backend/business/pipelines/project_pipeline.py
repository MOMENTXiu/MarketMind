"""Project CRUD orchestration."""

from __future__ import annotations

from pathlib import Path

from backend.core.errors import InfrastructureError, NotFoundError
from backend.models.project import Project, ProjectCreate, ProjectUpdate
from backend.providers.container import ProvidersContainer


class ProjectPipeline:
    """Orchestrate project CRUD using the project repository provider."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def create(self, data: ProjectCreate) -> Project:
        try:
            return self.providers.repository.create_project(data)
        except Exception as exc:
            raise InfrastructureError(f"创建项目失败: {exc}") from exc

    def list(self, skip: int = 0, limit: int = 100) -> tuple[list[Project], int]:
        try:
            items = self.providers.repository.list_projects(skip=skip, limit=limit)
            total = self.providers.repository.count_projects()
        except Exception as exc:
            raise InfrastructureError(f"读取项目列表失败: {exc}") from exc
        return items, total

    def get(self, project_id: str) -> Project:
        project = self.providers.repository.get_project(project_id)
        if project is None:
            raise NotFoundError(f"项目不存在: {project_id}")
        return project

    def update(self, project_id: str, update_data: ProjectUpdate) -> Project:
        project = self.providers.repository.update_project(project_id, update_data)
        if project is None:
            raise NotFoundError(f"项目不存在: {project_id}")
        return project

    def delete(self, project_id: str) -> bool:
        if self.providers.repository.get_project(project_id) is None:
            raise NotFoundError(f"项目不存在: {project_id}")
        try:
            return self.providers.repository.delete_project(project_id)
        except Exception as exc:
            raise InfrastructureError(f"删除项目失败: {exc}") from exc

    def resolve_report(self, project_id: str) -> tuple[Path, str]:
        """Return existing report path and frontend download filename."""

        project = self.get(project_id)
        if not project.results or not project.results.report_path:
            raise NotFoundError("报告文件不存在")
        path = Path(project.results.report_path)
        if not path.exists():
            raise NotFoundError("报告文件不存在")
        return path, f"{project.name}_分析报告.md"

    def resolve_audio(self, project_id: str) -> tuple[Path, str]:
        """Return existing project audio path and frontend download filename."""

        project = self.get(project_id)
        if not project.results or not project.results.audio_path:
            raise NotFoundError("语音文件不存在")
        path = Path(project.results.audio_path)
        if not path.exists():
            raise NotFoundError("语音文件不存在")
        return path, f"{project.name}_播报.mp3"
