"""Auth router for registration, login, and current user resolution."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth_dependencies import (
    get_current_user,
    get_issue_sse_ticket_pipeline,
    get_login_user_pipeline,
    get_register_user_pipeline,
)
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.issue_sse_ticket_pipeline import IssueSseTicketPipeline
from backend.business.pipelines.login_user_pipeline import LoginUserPipeline
from backend.business.pipelines.register_user_pipeline import RegisterUserPipeline
from backend.core.errors import (
    AuthError,
    DisabledUserError,
    DuplicateEmailError,
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidTokenError,
    NotFoundError,
)
from backend.models.auth import (
    SseTicketRequest,
    SseTicketResponse,
    TokenResponse,
    UserLoginRequest,
    UserMeResponse,
    UserRegisterRequest,
)
from backend.providers.auth_dtos import AuthenticatedUserContext, UserRegistrationInputDTO

router = APIRouter()


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    pipeline: RegisterUserPipeline = Depends(get_register_user_pipeline),
) -> dict:
    try:
        user = pipeline.execute(
            UserRegistrationInputDTO(
                email=payload.email,
                password=payload.password,
                display_name=payload.display_name,
            )
        )
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
        },
    }


@router.post("/auth/login")
async def login(
    payload: UserLoginRequest,
    pipeline: LoginUserPipeline = Depends(get_login_user_pipeline),
) -> dict:
    try:
        user, token_pair = pipeline.execute(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except DisabledUserError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthError as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": {
            "access_token": token_pair.access_token,
            "token_type": token_pair.token_type,
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
            },
        },
    }


@router.get("/auth/me")
async def me(
    user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
) -> dict:
    return {
        "success": True,
        "data": {
            "id": user.user_id,
            "email": user.email,
            "display_name": user.display_name,
        },
    }


@router.post("/auth/logout")
async def logout(
    user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
) -> dict:
    return {"success": True, "data": {}}


@router.post("/auth/sse-ticket")
async def create_sse_ticket(
    payload: SseTicketRequest,
    user: Annotated[AuthenticatedUserContext, Depends(get_current_user)],
    pipeline: IssueSseTicketPipeline = Depends(get_issue_sse_ticket_pipeline),
) -> dict:
    try:
        ticket = pipeline.execute(
            user_context=user,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            project_id=payload.project_id,
            job_id=payload.job_id,
            stream_type=payload.stream_type,
        )
    except AuthError as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": {
            "ticket": ticket.ticket,
            "expires_at": ticket.expires_at,
        },
    }
