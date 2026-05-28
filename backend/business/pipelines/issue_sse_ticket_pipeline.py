"""Issue SSE ticket business pipeline."""

from backend.abilities.auth.issue_sse_ticket import issue_sse_ticket
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
        return issue_sse_ticket(
            user_context=user_context,
            resource_type=resource_type,
            resource_id=resource_id,
            sse_ticket=self.providers.sse_ticket,
            project_repository=self.providers.repository,
            project_id=project_id,
            job_id=job_id,
            stream_type=stream_type,
        )
