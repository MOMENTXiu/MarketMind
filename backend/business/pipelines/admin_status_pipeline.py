"""Admin status pipeline — aggregates service health into summary."""

from __future__ import annotations

from backend.abilities.admin.aggregate_service_status import aggregate_service_status
from backend.providers.admin_dtos import AdminHealthSummaryDTO
from backend.providers.container import ProvidersContainer


class AdminStatusPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self._providers = providers

    def execute(self) -> AdminHealthSummaryDTO:
        health = self._providers.health
        if health is None:
            from backend.providers.admin_dtos import ServiceHealthDTO

            return AdminHealthSummaryDTO(
                overall_status="unknown",
                services=[
                    ServiceHealthDTO(
                        key="backend",
                        name="Python Backend",
                        category="app",
                        status="unknown",
                        message="Health provider not configured",
                    )
                ],
            )

        settings_available = self._providers.settings_inspection is not None
        alert_available = self._providers.alert is not None

        return aggregate_service_status(
            health=health,
            settings_available=settings_available,
            alert_available=alert_available,
        )
