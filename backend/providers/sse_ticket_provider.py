"""SSE ticket provider interface for minting and verifying EventSource tickets."""

from typing import Protocol

from backend.providers.auth_dtos import SseTicketDTO


class SseTicketProvider(Protocol):
    def mint_ticket(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        project_id: str | None = None,
        job_id: str | None = None,
        stream_type: str | None = None,
    ) -> SseTicketDTO:
        """Mint a short-lived SSE ticket bound to user and resource."""

    def verify_ticket(
        self,
        ticket: str,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        project_id: str | None = None,
        job_id: str | None = None,
        stream_type: str | None = None,
    ) -> SseTicketDTO:
        """Verify a ticket is valid, not consumed, not expired, and matches constraints.

        Raises:
            InvalidSseTicketError: when ticket is invalid, consumed, expired, or mismatched.
        """

    def consume_ticket(self, ticket: str) -> None:
        """Mark a ticket as consumed (one-time use)."""
