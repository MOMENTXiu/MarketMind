"""Admin status API router — GET /api/admin/status/summary."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.admin.dependencies import require_admin_user
from backend.api.dependencies import get_providers
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.admin_status_pipeline import AdminStatusPipeline
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.container import ProvidersContainer

router = APIRouter()


@router.get("/status/summary")
async def admin_status_summary(
    admin: Annotated[AuthenticatedUserContext, Depends(require_admin_user)],
    providers: ProvidersContainer = Depends(get_providers),
) -> dict:
    """Return aggregated service health for the admin status dashboard."""
    try:
        pipeline = AdminStatusPipeline(providers)
        summary = pipeline.execute()
    except Exception as exc:
        raise map_internal_error(exc) from exc

    return {
        "success": True,
        "data": {
            "overallStatus": summary.overall_status,
            "services": [
                {
                    "key": s.key,
                    "name": s.name,
                    "category": s.category,
                    "status": s.status,
                    "latencyMs": s.latency_ms,
                    "checkedAt": s.checked_at,
                    "message": s.message,
                    "version": s.version,
                }
                for s in summary.services
            ],
            "generatedAt": summary.generated_at,
        },
    }
