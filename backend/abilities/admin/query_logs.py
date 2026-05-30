"""Query and export log entries ability."""

from __future__ import annotations

from backend.providers.admin_dtos import (
    AdminLogPageDTO,
    AdminLogQueryDTO,
    AdminLogRecordDTO,
    ExportResultDTO,
)
from backend.providers.log_query_provider import LogQueryProvider


def query_event_logs(provider: LogQueryProvider, query: AdminLogQueryDTO) -> AdminLogPageDTO:
    """List event logs matching query filters."""
    return provider.list_events(query)


def query_audit_logs(provider: LogQueryProvider, query: AdminLogQueryDTO) -> AdminLogPageDTO:
    """List audit logs matching query filters."""
    return provider.list_audit(query)


def get_event_detail(provider: LogQueryProvider, event_id: str) -> AdminLogRecordDTO | None:
    """Get a single event by ID."""
    return provider.get_event(event_id)


def get_audit_detail(provider: LogQueryProvider, audit_id: str) -> AdminLogRecordDTO | None:
    """Get a single audit record by ID."""
    return provider.get_audit(audit_id)


def export_event_logs(
    provider: LogQueryProvider, query: AdminLogQueryDTO, fmt: str = "json"
) -> ExportResultDTO:
    """Export event logs in JSON or CSV format."""
    return provider.export_events(query, fmt)


def export_audit_logs(
    provider: LogQueryProvider, query: AdminLogQueryDTO, fmt: str = "json"
) -> ExportResultDTO:
    """Export audit logs in JSON or CSV format."""
    return provider.export_audit(query, fmt)
