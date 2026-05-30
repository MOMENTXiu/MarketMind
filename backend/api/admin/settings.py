"""Admin settings API router — GET /api/admin/settings, POST test endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.admin.dependencies import require_admin_user
from backend.api.dependencies import get_providers
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.admin_settings_pipeline import AdminSettingsPipeline
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.container import ProvidersContainer

router = APIRouter()


def _build_admin_context(user_ctx: AuthenticatedUserContext) -> dict:
    return {"user_id": user_ctx.user_id, "email": user_ctx.email}


def _serialize_settings(dto):
    """Serialize settings DTO, preserving camelCase keys for frontend."""
    if dto is None:
        return None
    if hasattr(dto, "__dataclass_fields__"):
        result = {}
        for f in dto.__dataclass_fields__:
            value = getattr(dto, f)
            if hasattr(value, "__dataclass_fields__"):
                result[to_camel(f)] = _serialize_settings(value)
            elif isinstance(value, list):
                result[to_camel(f)] = [
                    _serialize_settings(v) if hasattr(v, "__dataclass_fields__") else v
                    for v in value
                ]
            else:
                result[to_camel(f)] = value
        return result
    return dto


def to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


@router.get("/settings")
async def get_all_settings(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminSettingsPipeline(providers)
        result = pipeline.get_all_settings()
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "data": _serialize_settings(result)}


@router.post("/settings/llm/test")
async def test_llm(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminSettingsPipeline(providers)
        result = pipeline.test_llm(actor_id=admin.user_id)
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": {
            "success": result.success,
            "message": result.message,
            "latencyMs": result.latency_ms,
        },
    }


@router.post("/settings/alert/bark/test")
async def test_bark(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminSettingsPipeline(providers)
        result = pipeline.test_alert(actor_id=admin.user_id)
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": {
            "success": result.success,
            "message": result.message,
            "latencyMs": result.latency_ms,
        },
    }
