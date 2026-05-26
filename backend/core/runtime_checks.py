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
from typing import Any

from backend.core.config import Settings
from backend.core.errors import MarketMindError
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import LLMRequestDTO, LLMResponseDTO, SpeechSynthesisRequestDTO
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


def cmd_check_analysis_artifacts(args: argparse.Namespace) -> int:
    if not getattr(args, "sandbox", False):
        _emit("check-analysis-artifacts: refusing to run without --sandbox")
        return 1

    from backend.infrastructure.adapters.local_analysis_artifact_adapter import (
        LocalAnalysisArtifactAdapter,
    )
    from backend.infrastructure.adapters.local_analysis_model_store_adapter import (
        LocalAnalysisModelStoreAdapter,
    )

    project_id = "runtime-artifacts"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            artifacts = LocalAnalysisArtifactAdapter(tmp)
            models = LocalAnalysisModelStoreAdapter(tmp)
            json_ref = artifacts.save_json(project_id, "summary", {"ready": True})
            markdown_ref = artifacts.save_markdown(project_id, "report", "# Runtime Check")
            model_ref = models.save_model(project_id, "runtime_model", {"ready": True})

            resolved_json = artifacts.resolve_artifact(project_id, json_ref.id)
            loaded_model = models.load_model(project_id, "runtime_model")
            resolved_model = models.resolve_model(project_id, "runtime_model")
            refs = [json_ref, markdown_ref, model_ref]
            if resolved_json is None or resolved_model is None or loaded_model != {"ready": True}:
                _emit("check-analysis-artifacts: resolve/load mismatch")
                return 1
            for ref in refs:
                if ref.project_id != project_id:
                    _emit(f"check-analysis-artifacts: ref not project scoped: {ref.id}")
                    return 1
                if not ref.url.startswith(f"/api/analysis/projects/{project_id}/"):
                    _emit(f"check-analysis-artifacts: non-opaque url: {ref.url}")
                    return 1
                if Path(ref.storage_key).is_absolute() or ".." in Path(ref.storage_key).parts:
                    _emit(f"check-analysis-artifacts: unsafe storage key: {ref.storage_key}")
                    return 1
        except (MarketMindError, OSError, ValueError, TypeError) as exc:
            _emit(f"check-analysis-artifacts: failed: {exc}")
            return 1

    _emit("check-analysis-artifacts: ok sandbox=tmp")
    return 0


class _RuntimeCheckSpeechProvider:
    async def synthesize(self, request: SpeechSynthesisRequestDTO) -> Any:
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"runtime-check-audio")
        return type("SpeechResult", (), {"audio_path": request.output_path})()

    async def list_voices(self) -> list[dict[str, str]]:
        return [{"name": "runtime-check", "locale": "zh-CN"}]


class _RuntimeCheckLLMProvider:
    async def generate_text(self, request: LLMRequestDTO) -> LLMResponseDTO:
        return LLMResponseDTO(text="runtime check", provider=request.provider, model=request.model)


def _sandbox_provider_container(tmp: str) -> ProvidersContainer:
    from backend.infrastructure.adapters.console_telemetry_adapter import ConsoleTelemetryAdapter
    from backend.infrastructure.adapters.csv_dataset_adapter import CsvDatasetAdapter
    from backend.infrastructure.adapters.csv_retail_dataset_adapter import CsvRetailDatasetAdapter
    from backend.infrastructure.adapters.fastapi_background_analysis_job_adapter import (
        FastApiBackgroundAnalysisJobAdapter,
    )
    from backend.infrastructure.adapters.json_project_repository_adapter import (
        JsonProjectRepositoryAdapter,
    )
    from backend.infrastructure.adapters.local_analysis_artifact_adapter import (
        LocalAnalysisArtifactAdapter,
    )
    from backend.infrastructure.adapters.local_analysis_model_store_adapter import (
        LocalAnalysisModelStoreAdapter,
    )
    from backend.infrastructure.adapters.local_association_rule_store_adapter import (
        LocalAssociationRuleStoreAdapter,
    )
    from backend.infrastructure.adapters.local_generated_asset_adapter import (
        LocalGeneratedAssetAdapter,
    )
    from backend.infrastructure.adapters.local_project_file_storage_adapter import (
        LocalProjectFileStorageAdapter,
    )
    from backend.infrastructure.adapters.local_recommendation_model_store_adapter import (
        LocalRecommendationModelStoreAdapter,
    )
    from backend.infrastructure.adapters.local_regularized_dataset_adapter import (
        LocalRegularizedDatasetAdapter,
    )

    root = Path(tmp)
    return ProvidersContainer(
        repository=JsonProjectRepositoryAdapter(tmp),
        storage=LocalProjectFileStorageAdapter(tmp),
        assets=LocalGeneratedAssetAdapter(
            data_dir=tmp,
            outputs_dir=str(root / "outputs"),
            ai_audio_dir=str(root / "ai_audio"),
            temp_dir=str(root / "temp"),
        ),
        dataset=CsvDatasetAdapter(tmp),
        retail_dataset=CsvRetailDatasetAdapter(tmp),
        association_rules=LocalAssociationRuleStoreAdapter(),
        recommendation_models=LocalRecommendationModelStoreAdapter(str(root / "model_data.pkl")),
        analysis_artifacts=LocalAnalysisArtifactAdapter(tmp),
        analysis_models=LocalAnalysisModelStoreAdapter(tmp),
        speech=_RuntimeCheckSpeechProvider(),
        llm=_RuntimeCheckLLMProvider(),
        analysis_jobs=FastApiBackgroundAnalysisJobAdapter(),
        telemetry=ConsoleTelemetryAdapter(writer=lambda _line: None),
        regularized_dataset=LocalRegularizedDatasetAdapter(tmp),
    )


def _sample_retail_csv() -> bytes:
    return (
        "顾客编号,大类编码,大类名称,中类编码,中类名称,小类编码,小类名称,销售日期,"
        "销售月份,商品编码,规格型号,商品类型,单位,销售数量,销售金额,商品单价,是否促销\n"
        "1,10,食品,101,饮品,10101,茶饮,20240102,202401,SKU-1,500ml,标准,瓶,2,20,10,否\n"
    ).encode("utf-8")


def cmd_check_retail_analysis(args: argparse.Namespace) -> int:
    if not getattr(args, "sample", False):
        _emit("check-retail-analysis: refusing to run without --sample")
        return 1

    from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow

    with tempfile.TemporaryDirectory() as tmp:
        try:
            flow = RetailAnalysisFlow(_sandbox_provider_container(tmp))
            project = flow.create_project("Runtime Retail", "sandbox runtime check")
            upload = flow.upload_dataset(project["id"], "runtime.csv", _sample_retail_csv())
            listed = flow.list_projects()
            state = flow.get_project(project["id"])

            if listed["total"] != 1 or listed["projects"][0]["id"] != project["id"]:
                _emit("check-retail-analysis: project index/list mismatch")
                return 1
            if state["dataset_ref"] is None or not state["dataset_ref"]["url"].startswith(
                "/api/analysis/projects/"
            ):
                _emit("check-retail-analysis: missing opaque dataset ref")
                return 1
            if upload["quality_summary"].get("original_rows") != 1:
                _emit("check-retail-analysis: quality summary mismatch")
                return 1
        except (MarketMindError, OSError, ValueError, TypeError) as exc:
            _emit(f"check-retail-analysis: failed: {exc}")
            return 1

    _emit("check-retail-analysis: ok sample=tmp")
    return 0


def cmd_check_analysis_optional_runtime(_args: argparse.Namespace) -> int:
    from backend.infrastructure.factories.provider_factory import create_providers

    try:
        providers = create_providers(Settings())
    except (MarketMindError, OSError, ValueError, RuntimeError) as exc:
        _emit(f"check-analysis-optional-runtime: failed: {exc}")
        return 1

    required = {
        "retail_dataset": [
            "save_raw_sales",
            "load_raw_sales",
            "validate_raw_schema",
            "save_clean_sales",
            "load_clean_sales",
        ],
        "analysis_artifacts": ["save_json", "save_markdown", "save_table", "resolve_artifact"],
        "analysis_models": [
            "save_model",
            "load_model",
            "resolve_model",
            "list_models",
            "delete_model",
        ],
        "analysis_jobs": ["submit_project_analysis"],
        "telemetry": ["emit_debug", "emit_audit", "emit_error", "start_span", "end_span"],
    }
    for provider_name, method_names in required.items():
        provider = getattr(providers, provider_name)
        missing = [name for name in method_names if not callable(getattr(provider, name, None))]
        if missing:
            _emit(f"check-analysis-optional-runtime: {provider_name} missing {missing}")
            return 1

    _emit("check-analysis-optional-runtime: ok interfaces present")
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


def cmd_check_data_processing(args: argparse.Namespace) -> int:
    if not getattr(args, "sample", False):
        _emit("check-data-processing: refusing to run without --sample")
        return 1

    from backend.business.flows.data_processing_analysis_flow import DataProcessingAnalysisFlow

    with tempfile.TemporaryDirectory() as tmp:
        try:
            flow = DataProcessingAnalysisFlow(_sandbox_provider_container(tmp))
            job = flow.create_job("test-project", "Runtime Check")
            job_id = job["job_id"]

            sample = (
                "顾客编号,大类编码,大类名称,中类编码,中类名称,小类编码,小类名称,销售日期,"
                "销售月份,商品编码,规格型号,商品类型,单位,销售数量,销售金额,商品单价,是否促销\n"
                "1,10,食品,101,饮品,10101,茶饮,20240102,202401,SKU-1,500ml,标准,瓶,2,20,10,否\n"
            ).encode("utf-8")
            flow.upload_raw_dataset("test-project", job_id, "runtime.csv", sample)
            reg = flow.regularize("test-project", job_id)
            if reg["status"] not in {"queued", "completed", "needs_review"}:
                _emit("check-data-processing: unexpected regularization status")
                return 1
            if not reg.get("quality"):
                _emit("check-data-processing: missing quality summary")
                return 1
            if not reg.get("capability"):
                _emit("check-data-processing: missing capability summary")
                return 1
        except Exception as exc:
            _emit(f"check-data-processing: failed: {exc}")
            return 1

    _emit("check-data-processing: ok sample=tmp")
    return 0


def cmd_check_regularization(args: argparse.Namespace) -> int:
    if not getattr(args, "sandbox", False):
        _emit("check-regularization: refusing to run without --sandbox")
        return 1

    from backend.abilities.regularization.check_analysis_capability import check_analysis_capability
    from backend.abilities.regularization.check_data_quality import check_data_quality
    from backend.abilities.regularization.infer_schema_mapping import infer_schema_mapping
    from backend.abilities.regularization.normalize_business_fields import normalize_business_fields
    from backend.abilities.regularization.normalize_field_types import normalize_field_types
    from backend.abilities.regularization.profile_source_schema import profile_source_schema
    from backend.abilities.regularization.read_source_table import read_source_table

    with tempfile.TemporaryDirectory():
        try:
            sample = (
                "顾客编号,大类编码,大类名称,中类编码,中类名称,小类编码,小类名称,销售日期,"
                "销售月份,商品编码,规格型号,商品类型,单位,销售数量,销售金额,商品单价,是否促销\n"
                "1,10,食品,101,饮品,10101,茶饮,20240102,202401,SKU-1,500ml,标准,瓶,2,20,10,否\n"
            ).encode("utf-8")
            df, meta = read_source_table(sample, "test.csv")
            profile = profile_source_schema(df)
            mapping, detail = infer_schema_mapping(list(df.columns), profile)
            norm_df, _ = normalize_field_types(df, mapping)
            biz_df, rules = normalize_business_fields(norm_df)
            quality = check_data_quality(df, biz_df, mapping, 0)
            capability = check_analysis_capability(biz_df)

            if not mapping:
                _emit("check-regularization: empty mapping")
                return 1
            if quality["analysis_ready_score"] <= 0:
                _emit("check-regularization: invalid quality score")
                return 1
            if capability["runnable_count"] <= 0:
                _emit("check-regularization: no capabilities detected")
                return 1
        except Exception as exc:
            _emit(f"check-regularization: failed: {exc}")
            return 1

    _emit("check-regularization: ok sandbox=tmp")
    return 0


COMMANDS = {
    "check-config": cmd_check_config,
    "check-providers": cmd_check_providers,
    "check-storage": cmd_check_storage,
    "check-analysis-artifacts": cmd_check_analysis_artifacts,
    "check-retail-analysis": cmd_check_retail_analysis,
    "check-analysis-optional-runtime": cmd_check_analysis_optional_runtime,
    "check-llm": cmd_check_llm,
    "check-speech": cmd_check_speech,
    "validate-api-schemas": cmd_validate_api_schemas,
    "check-telemetry": cmd_check_telemetry,
    "check-audit-sink": cmd_check_audit_sink,
    "validate-log-schema": cmd_validate_log_schema,
    "validate-audit-schema": cmd_validate_audit_schema,
    "inspect-trace": cmd_inspect_trace,
    "check-data-processing": cmd_check_data_processing,
    "check-regularization": cmd_check_regularization,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backend.core.runtime_checks")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check-config")
    sub.add_parser("check-providers")

    p_storage = sub.add_parser("check-storage")
    p_storage.add_argument("--sandbox", action="store_true")

    p_artifacts = sub.add_parser("check-analysis-artifacts")
    p_artifacts.add_argument("--sandbox", action="store_true")

    p_retail = sub.add_parser("check-retail-analysis")
    p_retail.add_argument("--sample", action="store_true")

    sub.add_parser("check-analysis-optional-runtime")

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

    p_dp = sub.add_parser("check-data-processing")
    p_dp.add_argument("--sample", action="store_true")

    p_reg = sub.add_parser("check-regularization")
    p_reg.add_argument("--sandbox", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = COMMANDS[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
