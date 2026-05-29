"""Verify SSE ticket business pipeline."""

from backend.abilities.auth.verify_sse_ticket import verify_sse_ticket
from backend.core.errors import InvalidSseTicketError
from backend.providers.auth_dtos import SseTicketDTO
from backend.providers.container import ProvidersContainer


class VerifySseTicketPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def execute(
        self,
        ticket: str,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        project_id: str | None = None,
        job_id: str | None = None,
        stream_type: str | None = None,
    ) -> SseTicketDTO:
        if self.providers.sse_ticket is None:
            raise RuntimeError("SSE ticket provider not configured")
        result = verify_sse_ticket(
            ticket=ticket,
            sse_ticket=self.providers.sse_ticket,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            job_id=job_id,
            stream_type=stream_type,
        )
        # Consume one-time ticket after successful verification
        self.providers.sse_ticket.consume_ticket(ticket)
        return result
