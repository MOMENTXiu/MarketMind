"""Verify SSE ticket ability atom."""

from backend.providers.auth_dtos import SseTicketDTO
from backend.providers.sse_ticket_provider import SseTicketProvider


def verify_sse_ticket(
    ticket: str,
    sse_ticket: SseTicketProvider,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    project_id: str | None = None,
    job_id: str | None = None,
    stream_type: str | None = None,
) -> SseTicketDTO:
    return sse_ticket.verify_ticket(
        ticket=ticket,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
        job_id=job_id,
        stream_type=stream_type,
    )
