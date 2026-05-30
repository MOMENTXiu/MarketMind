"""Aggregate service health into an admin status summary ability."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.providers.admin_dtos import (
    AdminHealthSummaryDTO,
    ServiceHealthDTO,
    ServiceStatus,
)
from backend.providers.infrastructure_health_provider import InfrastructureHealthProvider


def aggregate_service_status(
    health: InfrastructureHealthProvider,
    settings_available: bool = False,
    alert_available: bool = False,
) -> AdminHealthSummaryDTO:
    """Aggregate health probes into a unified status summary.

    LLM and Bark availability is passed in by the caller (derived from
    SettingsInspectionProvider, not from live health probes).
    """
    components = health.check_all()
    services: list[ServiceHealthDTO] = []
    checked_at = datetime.now(UTC).isoformat()

    # Map known components from infra health provider
    component_map = {
        "backend": ("Python Backend", "app"),
        "postgres": ("PostgreSQL", "infra"),
        "redis": ("Redis", "infra"),
        "minio": ("MinIO", "infra"),
    }

    for key, info in components.items():
        name, category = component_map.get(key, (key.replace("_", " ").title(), "infra"))
        services.append(
            ServiceHealthDTO(
                key=key,
                name=name,
                category=category,
                status=info.get("status", "unknown"),
                latency_ms=info.get("latency_ms"),
                checked_at=checked_at,
                message=info.get("detail"),
                version=info.get("version") if key == "backend" else None,
            )
        )

    # Add external services based on settings availability
    if True:  # Always add LLM row
        services.append(
            ServiceHealthDTO(
                key="llm",
                name="LLM Provider",
                category="external",
                status="healthy" if settings_available else "unknown",
                checked_at=checked_at,
                message="Configured" if settings_available else "Not configured",
            )
        )

    services.append(
        ServiceHealthDTO(
            key="bark",
            name="Bark Alert",
            category="external",
            status="healthy" if alert_available else "unknown",
            checked_at=checked_at,
            message="Configured" if alert_available else "Not configured",
        )
    )

    # Compute overall status
    statuses = [s.status for s in services]
    if "down" in statuses:
        overall: ServiceStatus = "degraded"
    elif "degraded" in statuses:
        overall = "degraded"
    elif all(s == "healthy" for s in statuses):
        overall = "healthy"
    else:
        overall = "unknown"

    return AdminHealthSummaryDTO(
        overall_status=overall,
        services=services,
        generated_at=checked_at,
    )
