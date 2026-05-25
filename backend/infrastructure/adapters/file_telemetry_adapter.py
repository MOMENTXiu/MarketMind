"""File telemetry adapter."""

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from backend.providers.telemetry_dtos import (
    AuditEvent,
    DebugEvent,
    ErrorEvent,
    SpanContext,
    SpanHandle,
    TelemetryResult,
)


class FileTelemetryAdapter:
    """Best-effort telemetry adapter that appends structured JSONL events."""

    def __init__(self, event_log_path: str = "logs/telemetry/events.jsonl") -> None:
        self.event_log_path = Path(event_log_path)

    def emit_debug(self, event: DebugEvent) -> TelemetryResult:
        return self._append("debug", event)

    def emit_audit(self, event: AuditEvent) -> TelemetryResult:
        return self._append("audit", event)

    def emit_error(self, event: ErrorEvent) -> TelemetryResult:
        return self._append("error", event)

    def start_span(self, name: str, context: SpanContext | None = None) -> SpanHandle:
        span_context = context or SpanContext(trace_id=uuid4().hex, span_id=uuid4().hex)
        return SpanHandle(context=span_context, name=name)

    def end_span(self, span: SpanHandle, status: str = "completed") -> TelemetryResult:
        return self._append(
            "span",
            {"event": "span.ended", "name": span.name, "status": status, "context": span.context},
        )

    def _append(self, sink_event_type: str, payload: object) -> TelemetryResult:
        try:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.event_log_path, "a", encoding="utf-8") as file:
                file.write(
                    json.dumps(
                        {"type": sink_event_type, "payload": self._to_jsonable(payload)},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
            return TelemetryResult(success=True, sink="file")
        except Exception as exc:
            return TelemetryResult(success=False, sink="file", error_message=str(exc))

    def _to_jsonable(self, payload: object) -> object:
        if hasattr(payload, "__dataclass_fields__"):
            return asdict(payload)
        if isinstance(payload, dict):
            return {key: self._to_jsonable(value) for key, value in payload.items()}
        return payload
