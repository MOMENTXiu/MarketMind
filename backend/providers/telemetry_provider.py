"""Telemetry provider interface."""

from typing import Protocol

from backend.providers.telemetry_dtos import (
    AuditEvent,
    DebugEvent,
    ErrorEvent,
    SpanContext,
    SpanHandle,
    TelemetryResult,
)


class TelemetryProvider(Protocol):
    def emit_debug(self, event: DebugEvent) -> TelemetryResult:
        """Emit a debug event."""

    def emit_audit(self, event: AuditEvent) -> TelemetryResult:
        """Emit an audit event."""

    def emit_error(self, event: ErrorEvent) -> TelemetryResult:
        """Emit an error event."""

    def start_span(self, name: str, context: SpanContext | None = None) -> SpanHandle:
        """Start a trace span."""

    def end_span(self, span: SpanHandle, status: str = "completed") -> TelemetryResult:
        """End a trace span."""
