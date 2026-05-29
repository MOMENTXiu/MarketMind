"""Auth dependencies for FastAPI route injection."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.dependencies import get_providers, get_settings
from backend.core.config import Settings
from backend.business.pipelines.issue_sse_ticket_pipeline import IssueSseTicketPipeline
from backend.business.pipelines.login_user_pipeline import LoginUserPipeline
from backend.business.pipelines.register_user_pipeline import RegisterUserPipeline
from backend.business.pipelines.resolve_current_user_pipeline import ResolveCurrentUserPipeline
from backend.core.errors import (
    AuthError,
    DisabledUserError,
    ExpiredTokenError,
    InvalidTokenError,
    NotFoundError,
)
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.container import ProvidersContainer

_http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    providers: ProvidersContainer = Depends(get_providers),
) -> AuthenticatedUserContext:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        pipeline = ResolveCurrentUserPipeline(providers)
        return pipeline.execute(credentials.credentials)
    except (InvalidTokenError, ExpiredTokenError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except DisabledUserError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    providers: ProvidersContainer = Depends(get_providers),
) -> AuthenticatedUserContext | None:
    if credentials is None or not credentials.credentials:
        return None
    try:
        pipeline = ResolveCurrentUserPipeline(providers)
        return pipeline.execute(credentials.credentials)
    except AuthError:
        return None


async def get_current_user_or_enforce(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    providers: ProvidersContainer = Depends(get_providers),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUserContext | None:
    user = await get_current_user_optional(credentials, providers)
    if user is None and settings.AUTH_ENFORCE_ANALYSIS_AUTH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def get_register_user_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> RegisterUserPipeline:
    return RegisterUserPipeline(providers)


def get_login_user_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> LoginUserPipeline:
    return LoginUserPipeline(providers)


def get_issue_sse_ticket_pipeline(
    providers: ProvidersContainer = Depends(get_providers),
) -> IssueSseTicketPipeline:
    return IssueSseTicketPipeline(providers)
