"""Contract tests for telemetry adapters."""

from __future__ import annotations

import json

from backend.infrastructure.adapters.console_telemetry_adapter import ConsoleTelemetryAdapter
from backend.infrastructure.adapters.file_telemetry_adapter import FileTelemetryAdapter
from backend.providers.telemetry_dtos import AuditEvent, DebugEvent, ErrorEvent


def make_debug_event() -> DebugEvent:
    return DebugEvent(
        trace_id="trace-1",
        request_id="req-1",
        layer="ability",
        module="recommendation",
        operation="recommend",
        stage="execution",
        event="ability.completed",
        status="completed",
        redacted_fields=["raw_data"],
    )


def test_console_telemetry_adapter_writes_json_lines() -> None:
    lines: list[str] = []
    adapter = ConsoleTelemetryAdapter(writer=lines.append)

    debug_result = adapter.emit_debug(make_debug_event())
    span = adapter.start_span("pipeline")
    span_result = adapter.end_span(span)

    assert debug_result.success is True
    assert span_result.success is True
    assert len(lines) == 2
    assert json.loads(lines[0])["payload"]["event"] == "ability.completed"
    assert json.loads(lines[1])["payload"]["event"] == "span.ended"


def test_file_telemetry_adapter_appends_debug_audit_and_error_events(tmp_path) -> None:
    adapter = FileTelemetryAdapter(str(tmp_path / "telemetry/events.jsonl"))

    assert adapter.emit_debug(make_debug_event()).success is True
    assert (
        adapter.emit_audit(
            AuditEvent(
                actor_id="anonymous",
                action="project.analysis.completed",
                resource_type="project",
                resource_id="project-1",
                status="completed",
                trace_id="trace-1",
            )
        ).success
        is True
    )
    assert (
        adapter.emit_error(
            ErrorEvent(
                error_type="ProviderError",
                message="redacted",
                layer="adapter",
                module="llm",
                operation="generate_text",
            )
        ).success
        is True
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "telemetry/events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["type"] for row in rows] == ["debug", "audit", "error"]
    assert rows[1]["payload"]["action"] == "project.analysis.completed"


def test_telemetry_adapter_failures_are_best_effort() -> None:
    def broken_writer(line: str) -> None:
        raise OSError("sink unavailable")

    result = ConsoleTelemetryAdapter(writer=broken_writer).emit_debug(make_debug_event())

    assert result.success is False
    assert result.sink == "console"
    assert "sink unavailable" in (result.error_message or "")
