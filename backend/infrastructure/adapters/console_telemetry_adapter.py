"""Console telemetry adapter."""

import json
from collections.abc import Callable
from dataclasses import asdict
from uuid import uuid4

from backend.providers.telemetry_dtos import (
    AuditEvent,
    DebugEvent,
    ErrorEvent,
    SpanContext,
    SpanHandle,
    TelemetryResult,
)


class ConsoleTelemetryAdapter:
    """Best-effort telemetry adapter that writes structured JSON lines."""

    def __init__(self, writer: Callable[[str], None] | None = None) -> None:
        self.writer = writer or print

    def emit_debug(self, event: DebugEvent) -> TelemetryResult:
        return self._write("debug", event)

    def emit_audit(self, event: AuditEvent) -> TelemetryResult:
        return self._write("audit", event)

    def emit_error(self, event: ErrorEvent) -> TelemetryResult:
        return self._write("error", event)

    def start_span(self, name: str, context: SpanContext | None = None) -> SpanHandle:
        span_context = context or SpanContext(trace_id=uuid4().hex, span_id=uuid4().hex)
        return SpanHandle(context=span_context, name=name)

    def end_span(self, span: SpanHandle, status: str = "completed") -> TelemetryResult:
        return self._write(
            "span",
            {"event": "span.ended", "name": span.name, "status": status, "context": span.context},
        )

    def _write(self, sink_event_type: str, payload: object) -> TelemetryResult:
        try:
            self.writer(
                json.dumps(
                    {"type": sink_event_type, "payload": self._to_jsonable(payload)},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return TelemetryResult(success=True, sink="console")
        except Exception as exc:
            return TelemetryResult(success=False, sink="console", error_message=str(exc))

    def _to_jsonable(self, payload: object) -> object:
        if hasattr(payload, "__dataclass_fields__"):
            return asdict(payload)
        if isinstance(payload, dict):
            return {key: self._to_jsonable(value) for key, value in payload.items()}
        return payload
