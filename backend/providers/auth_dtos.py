"""Auth and user DTOs for provider boundary contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UserIdentityDTO:
    id: str
    email: str
    display_name: str | None = None
    status: str = "active"
    password_hash: str = ""
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class AuthenticatedUserContext:
    user_id: str
    email: str
    display_name: str | None = None


@dataclass(frozen=True)
class UserRegistrationInputDTO:
    email: str
    password: str
    display_name: str | None = None


@dataclass(frozen=True)
class AuthTokenClaimsDTO:
    sub: str
    email: str
    display_name: str | None = None
    iat: int | None = None
    exp: int | None = None
    aud: str | None = None
    iss: str | None = None


@dataclass(frozen=True)
class AuthTokenPairDTO:
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None


@dataclass(frozen=True)
class AuthSessionDTO:
    session_id: str
    user_id: str
    refresh_token_hash: str
    expires_at: str
    revoked_at: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class SseTicketDTO:
    ticket: str
    user_id: str
    resource_type: str
    resource_id: str
    project_id: str | None = None
    job_id: str | None = None
    stream_type: str | None = None
    expires_at: str | None = None
    consumed_at: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class OwnedResourceRefDTO:
    resource_type: str
    resource_id: str
    owner_user_id: str
    project_id: str | None = None
    job_id: str | None = None
