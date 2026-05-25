"""Dataset upload and reanalysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

from backend.core.errors import InfrastructureError, NotFoundError, ValidationError
from backend.models.project import Project, ProjectStatus, ProjectUpdate
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisJobDTO

ALLOWED_DATASET_SUFFIXES: tuple[str, ...] = (".csv", ".xlsx", ".xls")


@dataclass(frozen=True)
class UploadedFile:
    """Neutral DTO for an uploaded dataset payload."""

    filename: str
    stream: BinaryIO


@dataclass(frozen=True)
class UploadResult:
    project_id: str
    dataset_filename: str
    dataset_path: str
    status: ProjectStatus


class DatasetUploadPipeline:
    """Validate, persist, and submit datasets for analysis."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def upload(self, project_id: str, uploaded: UploadedFile) -> UploadResult:
        self._validate_filename(uploaded.filename)
        self._require_project(project_id)

        try:
            dataset_ref = self.providers.storage.save_dataset(
                project_id, uploaded.filename, uploaded.stream
            )
        except Exception as exc:
            raise InfrastructureError(f"保存数据集失败: {exc}") from exc

        updated = self.providers.repository.update_project(
            project_id,
            ProjectUpdate(
                status=ProjectStatus.PROCESSING,
                dataset_filename=uploaded.filename,
                dataset_path=str(dataset_ref.path),
            ),
        )
        if updated is None:
            raise NotFoundError(f"项目不存在: {project_id}")

        self._submit_analysis(project_id, trigger="upload")
        return UploadResult(
            project_id=project_id,
            dataset_filename=uploaded.filename,
            dataset_path=str(dataset_ref.path),
            status=ProjectStatus.PROCESSING,
        )

    def reanalyze(self, project_id: str) -> UploadResult:
        project = self._require_project(project_id)
        if not project.dataset_path:
            raise ValidationError("项目未上传数据集")

        updated = self.providers.repository.update_project(
            project_id, ProjectUpdate(status=ProjectStatus.PROCESSING)
        )
        if updated is None:
            raise NotFoundError(f"项目不存在: {project_id}")
        self._submit_analysis(project_id, trigger="reanalyze")
        return UploadResult(
            project_id=project_id,
            dataset_filename=project.dataset_filename or "",
            dataset_path=project.dataset_path,
            status=ProjectStatus.PROCESSING,
        )

    @staticmethod
    def _validate_filename(filename: str) -> None:
        if not filename:
            raise ValidationError("缺少上传文件名")
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in ALLOWED_DATASET_SUFFIXES:
            raise ValidationError("仅支持 CSV 和 Excel 文件")

    def _require_project(self, project_id: str) -> Project:
        project = self.providers.repository.get_project(project_id)
        if project is None:
            raise NotFoundError(f"项目不存在: {project_id}")
        return project

    def _submit_analysis(self, project_id: str, trigger: str) -> None:
        try:
            self.providers.analysis_jobs.submit_project_analysis(
                AnalysisJobDTO(project_id=project_id, trigger=trigger)
            )
        except InfrastructureError:
            raise
        except Exception as exc:
            raise InfrastructureError(f"提交分析任务失败: {exc}") from exc
