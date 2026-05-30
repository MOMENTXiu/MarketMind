"""Admin settings API router — GET /api/admin/settings, POST test endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.admin.dependencies import require_admin_user
from backend.api.dependencies import get_providers
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.admin_settings_pipeline import AdminSettingsPipeline
from backend.core.errors import NotFoundError, ValidationError
from backend.providers.admin_dtos import (
    EnvSettingsUpdateDTO,
    LlmConfigSaveDTO,
    SettingsEditDTO,
)
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


# ── .env edit ──────────────────────────────────────────────────────────────


@router.put("/settings/env")
async def update_env(
    payload: dict,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    """Update .env settings (LLM_* and BARK_* fields only)."""
    raw_updates = payload.get("updates", [])
    edits = [
        SettingsEditDTO(
            key=u.get("key", ""),
            value=u.get("value"),
            is_sensitive=u.get("isSensitive", False),
        )
        for u in raw_updates
    ]
    try:
        pipeline = AdminSettingsPipeline(providers)
        result = pipeline.update_env(admin.user_id, EnvSettingsUpdateDTO(updates=edits))
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": {
            "updated": list(result.keys()),
            "message": ".env updated. Restart backend for changes to take effect.",
        },
    }


# ── LLM config CRUD ────────────────────────────────────────────────────────


@router.get("/settings/llm-configs")
async def list_llm_configs(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminSettingsPipeline(providers)
        result = pipeline.get_llm_configs()
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": [
            {
                "id": c.id,
                "name": c.name,
                "provider": c.provider,
                "baseUrl": c.base_url,
                "apiKeyConfigured": c.api_key_configured,
                "model": c.model,
                "timeoutSeconds": c.timeout_seconds,
                "isActive": c.is_active,
                "createdAt": c.created_at,
            }
            for c in result.configs
        ],
    }


@router.post("/settings/llm-configs", status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    payload: dict,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    dto = LlmConfigSaveDTO(
        name=payload.get("name", ""),
        provider=payload.get("provider", "openai"),
        base_url=payload.get("baseUrl"),
        api_key=payload.get("apiKey"),
        model=payload.get("model"),
        timeout_seconds=payload.get("timeoutSeconds", 30),
        is_active=payload.get("isActive", False),
    )
    try:
        pipeline = AdminSettingsPipeline(providers)
        result = pipeline.create_llm_config(admin.user_id, dto)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "data": _llm_config_to_dict(result)}


@router.put("/settings/llm-configs/{config_id}")
async def update_llm_config(
    config_id: str,
    payload: dict,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    dto = LlmConfigSaveDTO(
        name=payload.get("name", ""),
        provider=payload.get("provider", "openai"),
        base_url=payload.get("baseUrl"),
        api_key=payload.get("apiKey"),
        model=payload.get("model"),
        timeout_seconds=payload.get("timeoutSeconds", 30),
        is_active=payload.get("isActive", False),
    )
    try:
        pipeline = AdminSettingsPipeline(providers)
        result = pipeline.update_llm_config(admin.user_id, config_id, dto)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "data": _llm_config_to_dict(result)}


@router.delete("/settings/llm-configs/{config_id}")
async def delete_llm_config(
    config_id: str,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminSettingsPipeline(providers)
        pipeline.delete_llm_config(admin.user_id, config_id)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "data": {"deleted": config_id}}


@router.post("/settings/llm-configs/{config_id}/activate")
async def activate_llm_config(
    config_id: str,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminSettingsPipeline(providers)
        result = pipeline.activate_llm_config(admin.user_id, config_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "data": _llm_config_to_dict(result)}


def _llm_config_to_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "provider": c.provider,
        "baseUrl": c.base_url,
        "apiKeyConfigured": c.api_key_configured,
        "model": c.model,
        "timeoutSeconds": c.timeout_seconds,
        "isActive": c.is_active,
        "createdAt": c.created_at,
    }
