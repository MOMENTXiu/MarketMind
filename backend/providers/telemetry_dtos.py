"""Telemetry DTOs shared across business and provider layers."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SpanContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    request_id: str | None = None


@dataclass(frozen=True)
class DebugEvent:
    layer: str
    module: str
    operation: str
    stage: str
    event: str
    status: str
    trace_id: str | None = None
    request_id: str | None = None
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
    redacted_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditEvent:
    actor_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    status: str
    trace_id: str | None = None
    request_id: str | None = None
    redaction_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorEvent:
    error_type: str
    message: str
    layer: str
    module: str
    operation: str
    trace_id: str | None = None
    request_id: str | None = None
    redacted_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TelemetryResult:
    success: bool
    sink: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class SpanHandle:
    context: SpanContext
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
