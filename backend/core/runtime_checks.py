"""Runtime checks CLI for MarketMind backend deployment self-tests.

Usage:
    python -m backend.core.runtime_checks <command> [args]

Commands are non-destructive by default. Sandbox/file-emitting commands use
:mod:`tempfile` and never touch real ``data/`` paths or secrets.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
from dataclasses import fields
from pathlib import Path

from backend.core.config import Settings
from backend.core.errors import MarketMindError
from backend.providers.container import ProvidersContainer
from backend.providers.telemetry_dtos import AuditEvent, DebugEvent, ErrorEvent


def _emit(message: str) -> None:
    print(message)


def cmd_check_config(_args: argparse.Namespace) -> int:
    try:
        settings = Settings()
    except (MarketMindError, OSError, ValueError) as exc:
        _emit(f"check-config: failed to load Settings: {exc}")
        return 1
    field_names = sorted(type(settings).model_fields.keys())
    _emit("check-config: ok")
    _emit(f"check-config: fields={field_names}")
    return 0


def cmd_check_providers(_args: argparse.Namespace) -> int:
    from backend.infrastructure.factories.provider_factory import create_providers

    try:
        providers = create_providers(Settings())
    except (MarketMindError, OSError, ValueError, RuntimeError) as exc:
        _emit(f"check-providers: failed: {exc}")
        return 1

    for container_field in fields(ProvidersContainer):
        value = getattr(providers, container_field.name)
        if value is None:
            _emit(f"check-providers: field {container_field.name} is None")
            return 1

    field_names = [container_field.name for container_field in fields(ProvidersContainer)]
    _emit("check-providers: ok")
    _emit(f"check-providers: fields={field_names}")
    return 0


def cmd_check_storage(args: argparse.Namespace) -> int:
    if not getattr(args, "sandbox", False):
        _emit("check-storage: refusing to run without --sandbox")
        return 1

    from backend.infrastructure.adapters.csv_dataset_adapter import CsvDatasetAdapter
    from backend.infrastructure.adapters.json_project_repository_adapter import (
        JsonProjectRepositoryAdapter,
    )
    from backend.infrastructure.adapters.local_project_file_storage_adapter import (
        LocalProjectFileStorageAdapter,
    )
    from backend.models.project import ProjectCreate

    with tempfile.TemporaryDirectory() as tmp:
        try:
            repo = JsonProjectRepositoryAdapter(tmp)
            created = repo.create_project(
                ProjectCreate(name="sandbox", description="runtime-check sandbox")
            )
            fetched = repo.get_project(created.id)
            if fetched is None or fetched.id != created.id:
                _emit("check-storage: project repository read mismatch")
                return 1

            storage = LocalProjectFileStorageAdapter(tmp)
            storage.save_dataset(created.id, "sandbox.csv", io.BytesIO(b"a,b\n1,2\n"))
            dataset = CsvDatasetAdapter(tmp).load_project_dataset(created.id)
            if dataset.shape[0] != 1:
                _emit(f"check-storage: dataset row count mismatch: {dataset.shape}")
                return 1

            if not repo.delete_project(created.id):
                _emit("check-storage: delete returned False")
                return 1
            if repo.get_project(created.id) is not None:
                _emit("check-storage: project still present after delete")
                return 1
        except (MarketMindError, OSError, ValueError) as exc:
            _emit(f"check-storage: failed: {exc}")
            return 1

    _emit("check-storage: ok sandbox=tmp")
    return 0


def cmd_check_llm(args: argparse.Namespace) -> int:
    if not getattr(args, "dry_run", False):
        _emit("check-llm: refusing to run without --dry-run (no real network calls allowed)")
        return 1

    from backend.infrastructure.factories.provider_factory import create_providers

    providers = create_providers(Settings())
    if not callable(getattr(providers.llm, "generate_text", None)):
        _emit("check-llm: provider missing callable generate_text()")
        return 1

    _emit("check-llm: dry-run skipped: requires network; provider interface present")
    return 0


def cmd_check_speech(args: argparse.Namespace) -> int:
    if not getattr(args, "mock", False):
        _emit("check-speech: refusing to run without --mock")
        return 1

    from backend.infrastructure.factories.provider_factory import create_providers

    providers = create_providers(Settings())
    if not callable(getattr(providers.speech, "synthesize", None)):
        _emit("check-speech: provider missing callable synthesize()")
        return 1

    _emit("check-speech: mock skipped: real synthesis not invoked; provider interface present")
    return 0


def cmd_validate_api_schemas(_args: argparse.Namespace) -> int:
    try:
        from backend.main import app

        schema = app.openapi()
    except Exception as exc:
        _emit(f"validate-api-schemas: failed: {exc}")
        return 1

    paths = schema.get("paths", {})
    if not paths:
        _emit("validate-api-schemas: no paths found")
        return 1

    _emit(f"validate-api-schemas: ok endpoints={len(paths)}")
    return 0


_TELEMETRY_TRACE_ID = "trace-runtime-check"
_TELEMETRY_REQUEST_ID = "req-runtime-check"


def cmd_check_telemetry(_args: argparse.Namespace) -> int:
    from backend.infrastructure.adapters.console_telemetry_adapter import ConsoleTelemetryAdapter

    captured: list[str] = []
    adapter = ConsoleTelemetryAdapter(writer=captured.append)

    debug_event = DebugEvent(
        layer="runtime_check",
        module="check_telemetry",
        operation="probe",
        stage="execution",
        event="probe.executed",
        status="completed",
        trace_id=_TELEMETRY_TRACE_ID,
        request_id=_TELEMETRY_REQUEST_ID,
    )
    if not adapter.emit_debug(debug_event).success:
        _emit("check-telemetry: debug emit failed")
        return 1

    audit_event = AuditEvent(
        actor_id="runtime-check",
        action="runtime.check.telemetry",
        resource_type="telemetry",
        resource_id=None,
        status="completed",
        trace_id=_TELEMETRY_TRACE_ID,
        request_id=_TELEMETRY_REQUEST_ID,
    )
    if not adapter.emit_audit(audit_event).success:
        _emit("check-telemetry: audit emit failed")
        return 1

    error_event = ErrorEvent(
        error_type="ProbeOnly",
        message="probe-only synthetic error",
        layer="runtime_check",
        module="check_telemetry",
        operation="probe",
        trace_id=_TELEMETRY_TRACE_ID,
        request_id=_TELEMETRY_REQUEST_ID,
    )
    if not adapter.emit_error(error_event).success:
        _emit("check-telemetry: error emit failed")
        return 1

    parsed = [json.loads(line) for line in captured]
    if len(parsed) != 3:
        _emit(f"check-telemetry: expected 3 events, got {len(parsed)}")
        return 1

    required = {
        "trace_id",
        "request_id",
        "layer",
        "module",
        "operation",
        "stage",
        "event",
        "status",
    }
    debug_payload = parsed[0]["payload"]
    missing = required - set(debug_payload.keys())
    if missing:
        _emit(f"check-telemetry: debug event missing fields: {sorted(missing)}")
        return 1

    _emit(f"check-telemetry: ok events_emitted={len(parsed)}")
    return 0


def cmd_check_audit_sink(_args: argparse.Namespace) -> int:
    from backend.infrastructure.adapters.file_telemetry_adapter import FileTelemetryAdapter

    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "telemetry" / "audit.jsonl"
        adapter = FileTelemetryAdapter(event_log_path=str(log_path))
        audit_event = AuditEvent(
            actor_id="runtime-check",
            action="runtime.check.audit",
            resource_type="audit_sink",
            resource_id="sandbox",
            status="completed",
            trace_id=_TELEMETRY_TRACE_ID,
            request_id=_TELEMETRY_REQUEST_ID,
        )
        result = adapter.emit_audit(audit_event)
        if not result.success or not log_path.exists():
            _emit(
                f"check-audit-sink: emit failed: success={result.success} path_exists={log_path.exists()}"
            )
            return 1

        lines = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not lines:
            _emit("check-audit-sink: no event written")
            return 1

        payload = lines[-1]["payload"]
        required = {
            "actor_id",
            "action",
            "resource_type",
            "resource_id",
            "status",
            "trace_id",
            "request_id",
        }
        missing = required - set(payload.keys())
        if missing:
            _emit(f"check-audit-sink: audit event missing fields: {sorted(missing)}")
            return 1

    _emit("check-audit-sink: ok sandbox=tmp")
    return 0


def _validate_against_dto(path: Path, dto_cls: type) -> tuple[bool, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"unreadable JSON {path}: {exc}"
    if not isinstance(data, dict):
        return False, f"expected object payload in {path}"
    required = {f.name for f in fields(dto_cls)}
    missing = required - set(data.keys())
    if missing:
        return False, f"{path} missing fields: {sorted(missing)}"
    return True, f"{path} fields_checked={sorted(required)}"


def cmd_validate_log_schema(args: argparse.Namespace) -> int:
    target = Path(getattr(args, "fixture", "tests/fixtures/logging/debug_event.json"))
    ok, msg = _validate_against_dto(target, DebugEvent)
    _emit(f"validate-log-schema: {'ok' if ok else 'failed'} {msg}")
    return 0 if ok else 1


def cmd_validate_audit_schema(args: argparse.Namespace) -> int:
    target = Path(getattr(args, "fixture", "tests/fixtures/logging/audit_event.json"))
    ok, msg = _validate_against_dto(target, AuditEvent)
    _emit(f"validate-audit-schema: {'ok' if ok else 'failed'} {msg}")
    return 0 if ok else 1


def cmd_inspect_trace(args: argparse.Namespace) -> int:
    trace_id = getattr(args, "trace_id", None)
    _emit(f"inspect-trace: skipped: not implemented in MVP (trace_id={trace_id})")
    return 0


COMMANDS = {
    "check-config": cmd_check_config,
    "check-providers": cmd_check_providers,
    "check-storage": cmd_check_storage,
    "check-llm": cmd_check_llm,
    "check-speech": cmd_check_speech,
    "validate-api-schemas": cmd_validate_api_schemas,
    "check-telemetry": cmd_check_telemetry,
    "check-audit-sink": cmd_check_audit_sink,
    "validate-log-schema": cmd_validate_log_schema,
    "validate-audit-schema": cmd_validate_audit_schema,
    "inspect-trace": cmd_inspect_trace,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backend.core.runtime_checks")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check-config")
    sub.add_parser("check-providers")

    p_storage = sub.add_parser("check-storage")
    p_storage.add_argument("--sandbox", action="store_true")

    p_llm = sub.add_parser("check-llm")
    p_llm.add_argument("--dry-run", action="store_true", dest="dry_run")

    p_speech = sub.add_parser("check-speech")
    p_speech.add_argument("--mock", action="store_true")

    sub.add_parser("validate-api-schemas")
    sub.add_parser("check-telemetry")
    sub.add_parser("check-audit-sink")

    p_log = sub.add_parser("validate-log-schema")
    p_log.add_argument("--fixture", default="tests/fixtures/logging/debug_event.json")

    p_audit = sub.add_parser("validate-audit-schema")
    p_audit.add_argument("--fixture", default="tests/fixtures/logging/audit_event.json")

    p_trace = sub.add_parser("inspect-trace")
    p_trace.add_argument("--trace-id", dest="trace_id", default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = COMMANDS[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
