"""Admin logs API router — GET /api/admin/logs/events, /audit, /export."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from backend.api.admin.dependencies import require_admin_user
from backend.api.dependencies import get_providers
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.admin_log_pipeline import AdminLogPipeline
from backend.providers.admin_dtos import AdminLogQueryDTO
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.container import ProvidersContainer

router = APIRouter()


def _build_query(
    level: str | None = None,
    event_type: str | None = None,
    actor_user_id: str | None = None,
    project_id: str | None = None,
    job_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> AdminLogQueryDTO:
    return AdminLogQueryDTO(
        level=level,
        event_type=event_type,
        actor_user_id=actor_user_id,
        project_id=project_id,
        job_id=job_id,
        request_id=request_id,
        trace_id=trace_id,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )


# ── Event logs ───────────────────────────────────────────────────────────────


@router.get("/logs/events")
async def list_events(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
    level: str | None = Query(None),
    event_type: str | None = Query(None),
    actor_user_id: str | None = Query(None),
    project_id: str | None = Query(None),
    job_id: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    offset: int = Query(0),
    limit: int = Query(50),
) -> dict:
    try:
        pipeline = AdminLogPipeline(providers)
        query = _build_query(
            level=level,
            event_type=event_type,
            actor_user_id=actor_user_id,
            project_id=project_id,
            job_id=job_id,
            from_date=from_date,
            to_date=to_date,
            offset=offset,
            limit=limit,
        )
        result = pipeline.list_events(query)
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": {
            "items": [_log_dto_to_dict(item) for item in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        },
    }


@router.get("/logs/events/{event_id}")
async def get_event(
    event_id: str,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminLogPipeline(providers)
        result = pipeline.get_event(event_id)
    except Exception as exc:
        raise map_internal_error(exc) from exc
    if result is None:
        return {"success": True, "data": None}
    return {"success": True, "data": _log_dto_to_dict(result)}


@router.get("/logs/events/export")
async def export_events(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
    fmt: str = Query("json", alias="format"),
    event_type: str | None = Query(None),
    level: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
) -> Response:
    try:
        pipeline = AdminLogPipeline(providers)
        query = _build_query(
            level=level,
            event_type=event_type,
            from_date=from_date,
            to_date=to_date,
        )
        result = pipeline.export_events(query, fmt)
    except Exception as exc:
        raise map_internal_error(exc) from exc

    media_type = "text/csv" if fmt == "csv" else "application/json"
    return Response(
        content=result.content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )


# ── Audit logs ───────────────────────────────────────────────────────────────


@router.get("/logs/audit")
async def list_audit(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
    actor_user_id: str | None = Query(None),
    action: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    offset: int = Query(0),
    limit: int = Query(50),
) -> dict:
    try:
        pipeline = AdminLogPipeline(providers)
        query = _build_query(
            event_type=action,
            actor_user_id=actor_user_id,
            from_date=from_date,
            to_date=to_date,
            offset=offset,
            limit=limit,
        )
        result = pipeline.list_audit(query)
    except Exception as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "data": {
            "items": [_log_dto_to_dict(item) for item in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        },
    }


@router.get("/logs/audit/{audit_id}")
async def get_audit(
    audit_id: str,
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    try:
        pipeline = AdminLogPipeline(providers)
        result = pipeline.get_audit(audit_id)
    except Exception as exc:
        raise map_internal_error(exc) from exc
    if result is None:
        return {"success": True, "data": None}
    return {"success": True, "data": _log_dto_to_dict(result)}


@router.get("/logs/audit/export")
async def export_audit(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
    fmt: str = Query("json", alias="format"),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
) -> Response:
    try:
        pipeline = AdminLogPipeline(providers)
        query = _build_query(from_date=from_date, to_date=to_date)
        result = pipeline.export_audit(query, fmt, actor_id=admin.user_id)
    except Exception as exc:
        raise map_internal_error(exc) from exc

    media_type = "text/csv" if fmt == "csv" else "application/json"
    return Response(
        content=result.content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _log_dto_to_dict(item) -> dict:
    return {
        "id": item.id,
        "level": item.level,
        "eventType": item.event_type,
        "message": item.message,
        "actorUserId": item.actor_user_id,
        "resourceType": item.resource_type,
        "resourceId": item.resource_id,
        "projectId": item.project_id,
        "jobId": item.job_id,
        "requestId": item.request_id,
        "traceId": item.trace_id,
        "createdAt": item.created_at,
        "metadata": item.metadata,
    }
