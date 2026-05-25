"""Project analysis job provider interface."""

from typing import Awaitable, Callable, Protocol

from backend.providers.dtos import AnalysisJobDTO

ProjectAnalysisCallable = Callable[[str], Awaitable[None] | None]


class AnalysisJobProvider(Protocol):
    def submit_project_analysis(
        self,
        job: AnalysisJobDTO,
        handler: ProjectAnalysisCallable | None = None,
    ) -> None:
        """Schedule or execute a project analysis job using bound or supplied handler."""
