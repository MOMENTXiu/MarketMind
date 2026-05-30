"""Log query provider interface.

JSONL file reading, pagination, and export belong in the Infrastructure
layer. Business layers query logs through this provider only.
"""

from __future__ import annotations

from typing import Protocol

from backend.providers.admin_dtos import (
    AdminLogPageDTO,
    AdminLogQueryDTO,
    AdminLogRecordDTO,
    ExportResultDTO,
)


class LogQueryProvider(Protocol):
    """Query and export structured telemetry/audit events."""

    def list_events(self, query: AdminLogQueryDTO) -> AdminLogPageDTO:
        """List event log entries matching the query filters."""

    def get_event(self, event_id: str) -> AdminLogRecordDTO | None:
        """Get a single event log entry by ID."""

    def export_events(self, query: AdminLogQueryDTO, fmt: str = "json") -> ExportResultDTO:
        """Export event log entries in JSON or CSV format."""

    def list_audit(self, query: AdminLogQueryDTO) -> AdminLogPageDTO:
        """List audit log entries matching the query filters."""

    def get_audit(self, audit_id: str) -> AdminLogRecordDTO | None:
        """Get a single audit log entry by ID."""

    def export_audit(self, query: AdminLogQueryDTO, fmt: str = "json") -> ExportResultDTO:
        """Export audit log entries in JSON or CSV format."""
