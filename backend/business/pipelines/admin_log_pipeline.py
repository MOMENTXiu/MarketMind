"""Admin log pipeline — query and export event/audit logs."""

from __future__ import annotations

from backend.abilities.admin.query_logs import (
    export_audit_logs,
    export_event_logs,
    get_audit_detail,
    get_event_detail,
    query_audit_logs,
    query_event_logs,
)
from backend.providers.admin_dtos import (
    AdminLogPageDTO,
    AdminLogQueryDTO,
    AdminLogRecordDTO,
    ExportResultDTO,
)
from backend.providers.container import ProvidersContainer
from backend.providers.telemetry_dtos import AuditEvent


class AdminLogPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self._providers = providers

    def _require_log_query(self):
        if self._providers.log_query is None:
            raise RuntimeError("Log query provider not configured")
        return self._providers.log_query

    # ── Event logs ──────────────────────────────────────────────────────

    def list_events(self, query: AdminLogQueryDTO) -> AdminLogPageDTO:
        return query_event_logs(self._require_log_query(), query)

    def get_event(self, event_id: str) -> AdminLogRecordDTO | None:
        return get_event_detail(self._require_log_query(), event_id)

    def export_events(self, query: AdminLogQueryDTO, fmt: str = "json") -> ExportResultDTO:
        return export_event_logs(self._require_log_query(), query, fmt)

    # ── Audit logs ──────────────────────────────────────────────────────

    def list_audit(self, query: AdminLogQueryDTO) -> AdminLogPageDTO:
        return query_audit_logs(self._require_log_query(), query)

    def get_audit(self, audit_id: str) -> AdminLogRecordDTO | None:
        return get_audit_detail(self._require_log_query(), audit_id)

    def export_audit(
        self,
        query: AdminLogQueryDTO,
        fmt: str = "json",
        actor_id: str | None = None,
    ) -> ExportResultDTO:
        result = export_audit_logs(self._require_log_query(), query, fmt)
        # Write self-audit: downloading audit logs is itself an audited action
        self._emit_audit(actor_id, "admin.download_audit_log")
        return result

    def _emit_audit(self, actor_id: str | None, action: str) -> None:
        telemetry = self._providers.telemetry
        if telemetry is None:
            return
        telemetry.emit_audit(
            AuditEvent(
                actor_id=actor_id,
                action=action,
                resource_type="audit_log",
                resource_id=None,
                status="success",
            )
        )
