"""Issue SSE ticket business pipeline."""

from backend.abilities.auth.issue_sse_ticket import issue_sse_ticket
from backend.core.errors import NotFoundError
from backend.providers.auth_dtos import AuthenticatedUserContext, SseTicketDTO
from backend.providers.container import ProvidersContainer


class IssueSseTicketPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def execute(
        self,
        user_context: AuthenticatedUserContext,
        resource_type: str,
        resource_id: str,
        project_id: str | None = None,
        job_id: str | None = None,
        stream_type: str | None = None,
    ) -> SseTicketDTO:
        if self.providers.sse_ticket is None:
            raise RuntimeError("SSE ticket provider not configured")

        # Validate project access using the same fallback as data_processing_analysis_flow
        if project_id is not None:
            found = False
            if self.providers.repository is not None:
                project = self.providers.repository.get_project(
                    project_id, owner_user_id=user_context.user_id
                )
                if project is not None:
                    found = True
            if not found and self.providers.retail_analysis_state is not None:
                state = self.providers.retail_analysis_state.get_state(
                    project_id, owner_user_id=user_context.user_id
                )
                if state is not None:
                    found = True
            if not found:
                raise NotFoundError("Project not found")

        return issue_sse_ticket(
            user_context=user_context,
            resource_type=resource_type,
            resource_id=resource_id,
            sse_ticket=self.providers.sse_ticket,
            project_repository=None,
            project_id=None,
            job_id=job_id,
            stream_type=stream_type,
        )
