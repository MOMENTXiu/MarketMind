"""Issue SSE ticket ability atom."""

from backend.core.errors import NotFoundError
from backend.providers.auth_dtos import AuthenticatedUserContext, SseTicketDTO
from backend.providers.project_repository_provider import ProjectRepositoryProvider
from backend.providers.sse_ticket_provider import SseTicketProvider


def issue_sse_ticket(
    user_context: AuthenticatedUserContext,
    resource_type: str,
    resource_id: str,
    sse_ticket: SseTicketProvider,
    project_repository: ProjectRepositoryProvider | None = None,
    project_id: str | None = None,
    job_id: str | None = None,
    stream_type: str | None = None,
) -> SseTicketDTO:
    if project_repository is not None and project_id is not None:
        project = project_repository.get_project(project_id, owner_user_id=user_context.user_id)
        if project is None:
            raise NotFoundError("Project not found")
    return sse_ticket.mint_ticket(
        user_id=user_context.user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
        job_id=job_id,
        stream_type=stream_type,
    )
