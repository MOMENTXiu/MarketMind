"""PostgreSQL-backed project repository external adapter."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.errors import InfrastructureError
from backend.infrastructure.db.models.project import ProjectRecord
from backend.models.project import (
    AnalysisParameters,
    AnalysisResults,
    Project,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
)

SessionFactory = Callable[[], Session]


class PostgresProjectRepositoryAdapter:
    """Project repository provider backed by SQLAlchemy sessions."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create_project(self, project_data: ProjectCreate) -> Project:
        project = Project(
            name=project_data.name,
            description=project_data.description,
            parameters=project_data.parameters or AnalysisParameters(),
        )
        record = self._record_from_project(project)
        try:
            with self._session_factory() as session:
                with session.begin():
                    session.add(record)
            return project
        except SQLAlchemyError as exc:
            raise InfrastructureError("Failed to create project metadata") from exc

    def get_project(self, project_id: str, owner_user_id: str | None = None) -> Project | None:
        try:
            with self._session_factory() as session:
                record = session.get(ProjectRecord, project_id)
                if record is None:
                    return None
                if owner_user_id is not None and record.owner_user_id != owner_user_id:
                    return None
                return self._project_from_record(record)
        except SQLAlchemyError as exc:
            raise InfrastructureError(f"Failed to get project metadata: {project_id}") from exc

    def list_projects(self, skip: int = 0, limit: int = 100, owner_user_id: str | None = None) -> list[Project]:
        try:
            with self._session_factory() as session:
                stmt = (
                    select(ProjectRecord)
                    .order_by(ProjectRecord.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
                if owner_user_id is not None:
                    stmt = stmt.where(ProjectRecord.owner_user_id == owner_user_id)
                records = session.scalars(stmt).all()
                return [self._project_from_record(record) for record in records]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Failed to list project metadata") from exc

    def update_project(self, project_id: str, update_data: ProjectUpdate) -> Project | None:
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.get(ProjectRecord, project_id)
                    if record is None:
                        return None
                    project = self._project_from_record(record)
                    updated_project = self._apply_update_data(project, update_data)
                    self._apply_project(record, updated_project)
                return self._project_from_record(record)
        except SQLAlchemyError as exc:
            raise InfrastructureError(f"Failed to update project metadata: {project_id}") from exc

    def mark_analysis_completed(self, project_id: str, results: AnalysisResults) -> Project | None:
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.get(ProjectRecord, project_id)
                    if record is None:
                        return None
                    project = self._project_from_record(record).model_copy(
                        update={
                            "status": ProjectStatus.COMPLETED,
                            "results": results,
                            "error_message": None,
                            "updated_at": datetime.now(),
                        }
                    )
                    self._apply_project(record, project)
                return self._project_from_record(record)
        except SQLAlchemyError as exc:
            raise InfrastructureError(f"Failed to complete project analysis: {project_id}") from exc

    def mark_analysis_failed(self, project_id: str, error_message: str) -> Project | None:
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.get(ProjectRecord, project_id)
                    if record is None:
                        return None
                    project = self._project_from_record(record).model_copy(
                        update={
                            "status": ProjectStatus.FAILED,
                            "error_message": error_message,
                            "updated_at": datetime.now(),
                        }
                    )
                    self._apply_project(record, project)
                return self._project_from_record(record)
        except SQLAlchemyError as exc:
            raise InfrastructureError(f"Failed to fail project analysis: {project_id}") from exc

    def delete_project(self, project_id: str, owner_user_id: str | None = None) -> bool:
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.get(ProjectRecord, project_id)
                    if record is None:
                        return False
                    if owner_user_id is not None and record.owner_user_id != owner_user_id:
                        return False
                    session.delete(record)
                    return True
        except SQLAlchemyError as exc:
            raise InfrastructureError(f"Failed to delete project metadata: {project_id}") from exc

    def count_projects(self, owner_user_id: str | None = None) -> int:
        try:
            with self._session_factory() as session:
                stmt = select(func.count()).select_from(ProjectRecord)
                if owner_user_id is not None:
                    stmt = stmt.where(ProjectRecord.owner_user_id == owner_user_id)
                return session.scalar(stmt) or 0
        except SQLAlchemyError as exc:
            raise InfrastructureError("Failed to count project metadata") from exc

    @staticmethod
    def _record_from_project(project: Project) -> ProjectRecord:
        return ProjectRecord(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status.value,
            metadata_json=PostgresProjectRepositoryAdapter._metadata_from_project(project),
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    @staticmethod
    def _apply_project(record: ProjectRecord, project: Project) -> None:
        record.name = project.name
        record.description = project.description
        record.status = project.status.value
        record.metadata_json = PostgresProjectRepositoryAdapter._metadata_from_project(project)
        record.created_at = project.created_at
        record.updated_at = project.updated_at

    @staticmethod
    def _apply_update_data(project: Project, update_data: ProjectUpdate) -> Project:
        if update_data.name is not None:
            project.name = update_data.name
        if update_data.description is not None:
            project.description = update_data.description
        if update_data.status is not None:
            project.status = update_data.status
        if update_data.parameters is not None:
            project.parameters = update_data.parameters
        if update_data.dataset_filename is not None:
            project.dataset_filename = update_data.dataset_filename
        if update_data.dataset_path is not None:
            project.dataset_path = update_data.dataset_path
        project.updated_at = datetime.now()
        return project

    @staticmethod
    def _metadata_from_project(project: Project) -> dict[str, Any]:
        return {
            "dataset_filename": project.dataset_filename,
            "dataset_path": project.dataset_path,
            "parameters": project.parameters.model_dump(),
            "results": project.results.model_dump() if project.results is not None else None,
            "error_message": project.error_message,
        }

    @staticmethod
    def _project_from_record(record: ProjectRecord) -> Project:
        metadata = record.metadata_json or {}
        parameters = metadata.get("parameters") or {}
        results = metadata.get("results")
        return Project(
            id=record.id,
            name=record.name,
            description=record.description,
            dataset_filename=metadata.get("dataset_filename"),
            dataset_path=metadata.get("dataset_path"),
            status=ProjectStatus(record.status),
            parameters=AnalysisParameters(**parameters),
            results=AnalysisResults(**results) if results is not None else None,
            error_message=metadata.get("error_message"),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
