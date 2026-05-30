"""Admin settings pipeline — inspect config and test connections."""

from __future__ import annotations

from backend.abilities.admin.inspect_settings import inspect_all_settings
from backend.abilities.admin.test_alert_connection import test_alert_connection
from backend.abilities.admin.test_llm_connection import test_llm_connection
from backend.providers.admin_dtos import AllSettingsDTO, TestResultDTO
from backend.providers.container import ProvidersContainer
from backend.providers.telemetry_dtos import AuditEvent, TelemetryResult


class AdminSettingsPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self._providers = providers

    def get_all_settings(self) -> AllSettingsDTO:
        inspector = self._providers.settings_inspection
        if inspector is None:
            return AllSettingsDTO()
        return inspect_all_settings(inspector)

    def test_llm(self, actor_id: str | None = None) -> TestResultDTO:
        inspector = self._providers.settings_inspection
        llm = self._providers.llm
        if inspector is None or llm is None:
            return TestResultDTO(success=False, message="LLM or settings provider not configured")

        result = test_llm_connection(inspector, llm)
        self._emit_audit(actor_id, "admin.test_llm", "setting", result)
        return result

    def test_alert(self, actor_id: str | None = None) -> TestResultDTO:
        alert = self._providers.alert
        if alert is None:
            return TestResultDTO(success=False, message="Alert provider not configured")

        result = test_alert_connection(alert)
        self._emit_audit(actor_id, "admin.test_alert", "setting", result)
        return result

    def _emit_audit(
        self,
        actor_id: str | None,
        action: str,
        resource_type: str,
        result: TestResultDTO,
    ) -> TelemetryResult:
        telemetry = self._providers.telemetry
        if telemetry is None:
            return TelemetryResult(success=False, sink=None, error_message="No telemetry provider")
        return telemetry.emit_audit(
            AuditEvent(
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=None,
                status="success" if result.success else "failed",
                redaction_summary={"message": result.message},
            )
        )
