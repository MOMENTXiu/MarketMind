"""FastAPI BackgroundTasks bridge for project analysis jobs."""

from inspect import isawaitable

from fastapi import BackgroundTasks

from backend.core.errors import InfrastructureError
from backend.providers.analysis_job_provider import ProjectAnalysisCallable
from backend.providers.dtos import AnalysisJobDTO


class FastApiBackgroundAnalysisJobAdapter:
    """Schedule project analysis using FastAPI BackgroundTasks when available."""

    def __init__(
        self,
        background_tasks: BackgroundTasks | None = None,
        default_handler: ProjectAnalysisCallable | None = None,
    ) -> None:
        self.background_tasks = background_tasks
        self.default_handler = default_handler

    def submit_project_analysis(
        self,
        job: AnalysisJobDTO,
        handler: ProjectAnalysisCallable | None = None,
    ) -> None:
        try:
            effective_handler = handler or self.default_handler
            if effective_handler is None:
                raise InfrastructureError(
                    "No project analysis handler is bound to the analysis job provider"
                )

            if self.background_tasks is not None:
                self.background_tasks.add_task(effective_handler, job.project_id)
                return

            result = effective_handler(job.project_id)
            if isawaitable(result):
                raise InfrastructureError(
                    "Async project analysis handler requires FastAPI BackgroundTasks"
                )
        except Exception as exc:
            if isinstance(exc, InfrastructureError):
                raise
            raise InfrastructureError(f"Project analysis scheduling failed: {exc}") from exc
