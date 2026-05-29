"""Fake auth provider implementations for testing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import jwt

from backend.core.errors import ExpiredTokenError, InvalidSseTicketError, InvalidTokenError
from backend.providers.auth_dtos import (
    AuthTokenClaimsDTO,
    SseTicketDTO,
    UserIdentityDTO,
    UserRegistrationInputDTO,
)
from backend.providers.auth_token_provider import AuthTokenProvider
from backend.providers.password_hasher_provider import PasswordHasherProvider
from backend.providers.sse_ticket_provider import SseTicketProvider
from backend.providers.user_directory_provider import UserDirectoryProvider


class FakePasswordHasherProvider(PasswordHasherProvider):
    def hash_password(self, plain_password: str) -> str:
        return f"$fake$hash${plain_password}"

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return hashed_password == f"$fake$hash${plain_password}"


class FakeUserDirectoryProvider(UserDirectoryProvider):
    def __init__(self) -> None:
        self.users: dict[str, UserIdentityDTO] = {}
        self._by_email: dict[str, str] = {}

    def create_user(self, input_dto: UserRegistrationInputDTO) -> UserIdentityDTO:
        user_id = f"user-{len(self.users) + 1}"
        user = UserIdentityDTO(
            id=user_id,
            email=input_dto.email.lower().strip(),
            display_name=input_dto.display_name,
            status="active",
            password_hash=input_dto.password,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        # Store password hash separately (not in DTO to avoid exposure)
        self.users[user_id] = user
        self._by_email[user.email] = user_id
        return user

    def find_user_by_email(self, email: str) -> UserIdentityDTO | None:
        user_id = self._by_email.get(email.lower().strip())
        return self.users.get(user_id) if user_id else None

    def find_user_by_id(self, user_id: str) -> UserIdentityDTO | None:
        return self.users.get(user_id)

    def update_user_status(self, user_id: str, status: str) -> UserIdentityDTO | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        updated = UserIdentityDTO(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=status,
            password_hash=user.password_hash,
            created_at=user.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )
        self.users[user_id] = updated
        return updated

    def update_last_login(self, user_id: str) -> UserIdentityDTO | None:
        return self.users.get(user_id)

    def set_password_hash(self, user_id: str, password_hash: str) -> None:
        """Test helper to associate a password hash with a user."""
        # Fake verifier just checks the hash format
        pass


class FakeAuthTokenProvider(AuthTokenProvider):
    def __init__(self, secret: str = "test-secret") -> None:
        self._secret = secret

    def sign_access_token(self, claims: AuthTokenClaimsDTO) -> str:
        now = datetime.now(UTC)
        exp = now + timedelta(hours=1)
        payload = {
            "sub": claims.sub,
            "email": claims.email,
            "display_name": claims.display_name,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def verify_access_token(self, token: str) -> AuthTokenClaimsDTO:
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError("Token has expired") from exc
        except Exception as exc:
            raise InvalidTokenError(f"Invalid token: {exc}") from exc
        return AuthTokenClaimsDTO(
            sub=payload.get("sub", ""),
            email=payload.get("email", ""),
            display_name=payload.get("display_name"),
            iat=payload.get("iat"),
            exp=payload.get("exp"),
        )

    def make_expired_token(self, claims: AuthTokenClaimsDTO) -> str:
        now = datetime.now(UTC)
        exp = now - timedelta(seconds=1)
        payload = {
            "sub": claims.sub,
            "email": claims.email,
            "display_name": claims.display_name,
            "iat": int((now - timedelta(hours=1)).timestamp()),
            "exp": int(exp.timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")


class FakeSseTicketProvider(SseTicketProvider):
    def __init__(self) -> None:
        self._tickets: dict[str, SseTicketDTO] = {}
        self._consumed: set[str] = set()

    def mint_ticket(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        project_id: str | None = None,
        job_id: str | None = None,
        stream_type: str | None = None,
    ) -> SseTicketDTO:
        ticket = f"ticket-{len(self._tickets) + 1}"
        dto = SseTicketDTO(
            ticket=ticket,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            job_id=job_id,
            stream_type=stream_type,
            expires_at=(datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            created_at=datetime.now(UTC).isoformat(),
        )
        self._tickets[ticket] = dto
        return dto

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
        dto = self._tickets.get(ticket)
        if dto is None:
            raise InvalidSseTicketError("Ticket not found")
        if ticket in self._consumed:
            raise InvalidSseTicketError("Ticket already consumed")
        if user_id is not None and dto.user_id != user_id:
            raise InvalidSseTicketError("Ticket user mismatch")
        if resource_type is not None and dto.resource_type != resource_type:
            raise InvalidSseTicketError("Ticket resource type mismatch")
        if resource_id is not None and dto.resource_id != resource_id:
            raise InvalidSseTicketError("Ticket resource id mismatch")
        if project_id is not None and dto.project_id != project_id:
            raise InvalidSseTicketError("Ticket project mismatch")
        if job_id is not None and dto.job_id != job_id:
            raise InvalidSseTicketError("Ticket job mismatch")
        if stream_type is not None and dto.stream_type != stream_type:
            raise InvalidSseTicketError("Ticket stream type mismatch")
        return dto

    def consume_ticket(self, ticket: str) -> None:
        self._consumed.add(ticket)

    def expire_ticket(self, ticket: str) -> None:
        dto = self._tickets.get(ticket)
        if dto is not None:
            expired = SseTicketDTO(
                ticket=dto.ticket,
                user_id=dto.user_id,
                resource_type=dto.resource_type,
                resource_id=dto.resource_id,
                project_id=dto.project_id,
                job_id=dto.job_id,
                stream_type=dto.stream_type,
                expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
                created_at=dto.created_at,
            )
            self._tickets[ticket] = expired
