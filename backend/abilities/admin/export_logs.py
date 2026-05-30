"""Export log entries ability (thin re-export for explicit module naming)."""

from __future__ import annotations

from backend.abilities.admin.query_logs import export_audit_logs, export_event_logs

__all__ = ["export_audit_logs", "export_event_logs"]
