"""PostgreSQL user directory adapter."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.errors import DuplicateEmailError
from backend.infrastructure.db.models.user import UserRecord
from backend.providers.auth_dtos import UserIdentityDTO, UserRegistrationInputDTO
from backend.providers.user_directory_provider import UserDirectoryProvider


class PostgresUserDirectoryAdapter(UserDirectoryProvider):
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    def create_user(self, input_dto: UserRegistrationInputDTO) -> UserIdentityDTO:
        now = datetime.now(UTC)
        user_id = uuid4().hex
        record = UserRecord(
            id=user_id,
            email=input_dto.email.lower().strip(),
            password_hash=input_dto.password,  # assumed pre-hashed by caller
            display_name=input_dto.display_name,
            status="active",
            created_at=now,
            updated_at=now,
        )
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            existing = session.execute(
                select(UserRecord).where(UserRecord.email == record.email)
            ).scalar_one_or_none()
            if existing is not None:
                raise DuplicateEmailError(f"User with email {record.email} already exists")
            session.add(record)
            session.commit()
        return _to_dto(record)

    def find_user_by_email(self, email: str) -> UserIdentityDTO | None:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            record = session.execute(
                select(UserRecord).where(UserRecord.email == email.lower().strip())
            ).scalar_one_or_none()
            return _to_dto(record) if record else None

    def find_user_by_id(self, user_id: str) -> UserIdentityDTO | None:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            record = session.get(UserRecord, user_id)
            return _to_dto(record) if record else None

    def update_user_status(self, user_id: str, status: str) -> UserIdentityDTO | None:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            record = session.get(UserRecord, user_id)
            if record is None:
                return None
            record.status = status
            record.updated_at = datetime.now(UTC)
            session.commit()
            return _to_dto(record)

    def update_last_login(self, user_id: str) -> UserIdentityDTO | None:
        with self._session_factory() as session:
            session = session if isinstance(session, Session) else session.sync_session
            record = session.get(UserRecord, user_id)
            if record is None:
                return None
            record.last_login_at = datetime.now(UTC)
            record.updated_at = datetime.now(UTC)
            session.commit()
            return _to_dto(record)


def _to_dto(record: UserRecord) -> UserIdentityDTO:
    return UserIdentityDTO(
        id=record.id,
        email=record.email,
        display_name=record.display_name,
        status=record.status,
        password_hash=record.password_hash,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )

