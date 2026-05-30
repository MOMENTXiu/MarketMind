"""Admin settings pipeline — inspect config, edit .env, manage LLM configs."""

from __future__ import annotations

from backend.abilities.admin.inspect_settings import inspect_all_settings
from backend.abilities.admin.manage_llm_config import (
    activate_llm_config,
    create_llm_config,
    delete_llm_config,
    get_llm_config,
    list_llm_configs,
    update_llm_config,
)
from backend.abilities.admin.manage_settings import update_env_settings
from backend.abilities.admin.test_alert_connection import test_alert_connection
from backend.abilities.admin.test_llm_connection import test_llm_connection
from backend.providers.admin_dtos import (
    AllSettingsDTO,
    EnvSettingsUpdateDTO,
    LlmConfigItemDTO,
    LlmConfigListDTO,
    LlmConfigSaveDTO,
    TestResultDTO,
)
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

    def update_env(
        self,
        actor_id: str | None,
        dto: EnvSettingsUpdateDTO,
    ) -> dict[str, str]:
        env_file = self._providers.env_file
        if env_file is None:
            raise RuntimeError("Env file provider not configured")
        result = update_env_settings(dto, env_file)
        self._emit_audit_simple(actor_id, "admin.update_env", "setting", "success")
        return result

    # ── LLM config CRUD ──────────────────────────────────────────────

    def get_llm_configs(self) -> LlmConfigListDTO:
        env_file = self._providers.env_file
        if env_file is None:
            return LlmConfigListDTO()
        return list_llm_configs(env_file)

    def get_llm_config_detail(self, config_id: str) -> LlmConfigItemDTO:
        env_file = self._providers.env_file
        if env_file is None:
            raise RuntimeError("Env file provider not configured")
        return get_llm_config(env_file, config_id)

    def create_llm_config(
        self,
        actor_id: str | None,
        dto: LlmConfigSaveDTO,
    ) -> LlmConfigItemDTO:
        env_file = self._providers.env_file
        if env_file is None:
            raise RuntimeError("Env file provider not configured")
        result = create_llm_config(env_file, dto)
        self._emit_audit_simple(actor_id, "admin.create_llm_config", "setting", "success")
        return result

    def update_llm_config(
        self,
        actor_id: str | None,
        config_id: str,
        dto: LlmConfigSaveDTO,
    ) -> LlmConfigItemDTO:
        env_file = self._providers.env_file
        if env_file is None:
            raise RuntimeError("Env file provider not configured")
        result = update_llm_config(env_file, config_id, dto)
        self._emit_audit_simple(actor_id, "admin.update_llm_config", "setting", "success")
        return result

    def delete_llm_config(self, actor_id: str | None, config_id: str) -> bool:
        env_file = self._providers.env_file
        if env_file is None:
            raise RuntimeError("Env file provider not configured")
        result = delete_llm_config(env_file, config_id)
        self._emit_audit_simple(actor_id, "admin.delete_llm_config", "setting", "success")
        return result

    def activate_llm_config(
        self,
        actor_id: str | None,
        config_id: str,
    ) -> LlmConfigItemDTO:
        env_file = self._providers.env_file
        if env_file is None:
            raise RuntimeError("Env file provider not configured")
        result = activate_llm_config(env_file, config_id)
        self._emit_audit_simple(actor_id, "admin.activate_llm_config", "setting", "success")
        return result

    # ── Internal ──────────────────────────────────────────────────────

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

    def _emit_audit_simple(
        self,
        actor_id: str | None,
        action: str,
        resource_type: str,
        status: str,
    ) -> None:
        telemetry = self._providers.telemetry
        if telemetry is None:
            return
        telemetry.emit_audit(
            AuditEvent(
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=None,
                status=status,
            )
        )
