"""PostgreSQL SSE ticket adapter."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.errors import InfrastructureError, InvalidSseTicketError
from backend.infrastructure.db.models.sse_ticket import SseTicketRecord
from backend.providers.auth_dtos import SseTicketDTO
from backend.providers.sse_ticket_provider import SseTicketProvider


class PostgresSseTicketAdapter(SseTicketProvider):
    def __init__(self, session_factory: Any, expire_minutes: int = 5) -> None:
        self._session_factory = session_factory
        self._expire_minutes = expire_minutes

    def mint_ticket(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        project_id: str | None = None,
        job_id: str | None = None,
        stream_type: str | None = None,
    ) -> SseTicketDTO:
        raw = uuid4().hex + uuid4().hex
        ticket_hash = sha256(raw.encode()).hexdigest()
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=self._expire_minutes)
        record = SseTicketRecord(
            id=uuid4().hex,
            ticket_hash=ticket_hash,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            job_id=job_id,
            stream_type=stream_type,
            expires_at=expires,
            created_at=now,
        )
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            session.add(record)
            session.commit()
        return _to_dto(record, raw)

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
        ticket_hash = sha256(ticket.encode()).hexdigest()
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            record = session.execute(
                select(SseTicketRecord).where(SseTicketRecord.ticket_hash == ticket_hash)
            ).scalar_one_or_none()
            if record is None:
                raise InvalidSseTicketError("Ticket not found")
            if record.consumed_at is not None:
                raise InvalidSseTicketError("Ticket already consumed")
            if record.expires_at < datetime.now(UTC):
                raise InvalidSseTicketError("Ticket expired")
            if user_id is not None and record.user_id != user_id:
                raise InvalidSseTicketError("Ticket user mismatch")
            if resource_type is not None and record.resource_type != resource_type:
                raise InvalidSseTicketError("Ticket resource type mismatch")
            if resource_id is not None and record.resource_id != resource_id:
                raise InvalidSseTicketError("Ticket resource id mismatch")
            if project_id is not None and record.project_id != project_id:
                raise InvalidSseTicketError("Ticket project mismatch")
            if job_id is not None and record.job_id != job_id:
                raise InvalidSseTicketError("Ticket job mismatch")
            if stream_type is not None and record.stream_type != stream_type:
                raise InvalidSseTicketError("Ticket stream type mismatch")
            return _to_dto(record, ticket)

    def consume_ticket(self, ticket: str) -> None:
        ticket_hash = sha256(ticket.encode()).hexdigest()
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            record = session.execute(
                select(SseTicketRecord).where(SseTicketRecord.ticket_hash == ticket_hash)
            ).scalar_one_or_none()
            if record is not None:
                record.consumed_at = datetime.now(UTC)
                session.commit()


def _to_dto(record: SseTicketRecord, raw_ticket: str) -> SseTicketDTO:
    return SseTicketDTO(
        ticket=raw_ticket,
        user_id=record.user_id,
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        project_id=record.project_id,
        job_id=record.job_id,
        stream_type=record.stream_type,
        expires_at=record.expires_at.isoformat() if record.expires_at else None,
        consumed_at=record.consumed_at.isoformat() if record.consumed_at else None,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )

from typing import Any  # noqa: E402
