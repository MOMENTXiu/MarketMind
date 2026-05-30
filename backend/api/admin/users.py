"""Admin users API router — GET/PATCH /api/admin/users."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.admin.dependencies import require_admin_user
from backend.api.dependencies import get_providers
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.admin_user_pipeline import AdminUserPipeline
from backend.core.errors import NotFoundError, ValidationError
from backend.providers.admin_dtos import UpdateRoleDTO, UpdateStatusDTO
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.container import ProvidersContainer

router = APIRouter()


@router.get("/users")
async def list_users(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
    search: str | None = Query(None),
    offset: int = Query(0),
    limit: int = Query(50),
) -> dict:
    try:
        pipeline = AdminUserPipeline(providers)
        users = pipeline.list_users(search=search, offset=offset, limit=limit)
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": [_user_list_item_to_dict(u) for u in users],
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminUserPipeline(providers)
        detail = pipeline.get_user_detail(user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": _user_detail_to_dict(detail),
    }


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    payload: dict,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    new_role = payload.get("role", "user")
    if new_role not in ("user", "admin"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role must be 'user' or 'admin'",
        )

    try:
        pipeline = AdminUserPipeline(providers)
        updated = pipeline.update_user_role(
            actor_id=admin.user_id,
            target_id=user_id,
            dto=UpdateRoleDTO(role=new_role),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": _user_list_item_to_dict(updated),
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    payload: dict,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    new_status = payload.get("status", "active")
    if new_status not in ("active", "disabled"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be 'active' or 'disabled'",
        )

    try:
        pipeline = AdminUserPipeline(providers)
        updated = pipeline.update_user_status(
            actor_id=admin.user_id,
            target_id=user_id,
            dto=UpdateStatusDTO(status=new_status),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": _user_list_item_to_dict(updated),
    }


# ── Serialization helpers ────────────────────────────────────────────────────


def _user_list_item_to_dict(u) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "displayName": u.display_name,
        "role": u.role,
        "status": u.status,
        "projectCount": u.project_count,
        "lastLoginAt": u.last_login_at,
        "createdAt": u.created_at,
    }


def _user_detail_to_dict(d) -> dict:
    return {
        "id": d.id,
        "email": d.email,
        "displayName": d.display_name,
        "role": d.role,
        "status": d.status,
        "projectCount": d.project_count,
        "projects": [
            {"id": p.id, "name": p.name, "status": p.status, "createdAt": p.created_at}
            for p in d.projects
        ],
        "lastLoginAt": d.last_login_at,
        "createdAt": d.created_at,
        "updatedAt": d.updated_at,
    }
