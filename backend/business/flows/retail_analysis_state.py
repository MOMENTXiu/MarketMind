"""Retail Analysis V2 state shaping helpers."""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from typing import Any

from backend.providers.analysis_event_stream_provider import project_channel
from backend.providers.dtos import (
    AnalysisStateEventDTO,
    RetailAnalysisProjectStateDTO,
    RetailAnalysisProjectSummaryDTO,
    RetailAnalysisRunInfoDTO,
)

PROJECT_STATUSES = frozenset({"queued", "processing", "completed", "failed", "needs_review"})
STAGE_STATUSES = frozenset({"queued", "processing", "completed", "failed", "skipped"})
STAGE_NAMES = (
    "dataset_preparation",
    "feature_engineering",
    "segmentation",
    "association",
    "recommendation",
    "marketer_insights",
    "report",
)

MARKETER_INSIGHT_KEYS = (
    "segment_value",
    "promotion_effect",
    "bundle_strategy",
    "category_strategy",
)


def new_stage(stage_name: str) -> dict[str, Any]:
    return {"stage": stage_name, "status": "queued", "error": None, "artifact_refs": []}


def project_view(state: dict[str, Any]) -> dict[str, Any]:
    summary = state.get("summary") or {}
    analysis_kind = summary.get("analysis_kind") if isinstance(summary, dict) else None
    dp_job_id = summary.get("job_id") if isinstance(summary, dict) else None
    effective_job_id = dp_job_id or state.get("job_id")
    return {
        "id": state["id"],
        "name": state["name"],
        "description": state.get("description", ""),
        "status": state["status"],
        "analysis_kind": analysis_kind,
        "dataset_ref": public_ref(state["dataset_ref"]) if state.get("dataset_ref") else None,
        "dataset_filename": _dataset_filename(state),
        "quality_summary": sanitize(state.get("quality_summary", {})),
        "artifact_refs": [public_ref(ref) for ref in state.get("artifact_refs", [])],
        "recommendations": sanitize(state.get("recommendations", [])),
        "marketer_insights": sanitize(state.get("marketer_insights", empty_marketer_insights())),
        "stage_statuses": list(state.get("stage_statuses", [])),
        "summary": dict(summary) if isinstance(summary, dict) else {},
        "job_id": effective_job_id,
        "trace_id": state.get("trace_id"),
        "error": state.get("error"),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
    }


def project_view_from_summary(summary: RetailAnalysisProjectSummaryDTO) -> dict[str, Any]:
    return project_view(
        _state_payload(
            project_id=summary.id,
            name=summary.name,
            description=summary.description,
            status=summary.status,
            stage_statuses=summary.stage_statuses,
            summary=summary.summary,
            dataset_ref=summary.dataset_ref,
            quality_summary=summary.quality_summary,
            artifact_refs=summary.artifact_refs,
            recommendations=summary.recommendations,
            marketer_insights=summary.marketer_insights,
            run_info=summary.run_info,
            job_id=summary.job_id,
            trace_id=summary.trace_id,
            error=summary.error,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )
    )


def state_from_provider_dto(state: RetailAnalysisProjectStateDTO) -> dict[str, Any]:
    return _state_payload(
        project_id=state.id,
        name=state.name,
        description=state.description,
        status=state.status,
        stage_statuses=state.stage_statuses,
        summary=state.summary,
        dataset_ref=state.dataset_ref,
        quality_summary=state.quality_summary,
        artifact_refs=state.artifact_refs,
        recommendations=state.recommendations,
        marketer_insights=state.marketer_insights,
        run_info=state.run_info,
        job_id=state.run_info.job_id if state.run_info is not None else None,
        trace_id=state.run_info.trace_id if state.run_info is not None else None,
        error=state.error,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


def state_to_provider_dto(state: dict[str, Any]) -> RetailAnalysisProjectStateDTO:
    return RetailAnalysisProjectStateDTO(
        id=str(state["id"]),
        name=str(state.get("name") or ""),
        description=str(state.get("description") or ""),
        status=str(state.get("status") or "queued"),
        stage_statuses=sanitize(state.get("stage_statuses", [])),
        summary=sanitize(state.get("summary", {})),
        dataset_ref=sanitize(state.get("dataset_ref")) if state.get("dataset_ref") else None,
        quality_summary=sanitize(state.get("quality_summary", {})),
        artifact_refs=sanitize(state.get("artifact_refs", [])),
        recommendations=sanitize(state.get("recommendations", [])),
        marketer_insights=sanitize(state.get("marketer_insights", empty_marketer_insights())),
        run_info=_run_info_dto_from_state(state),
        error=_optional_str(state.get("error")),
        created_at=_optional_str(state.get("created_at")),
        updated_at=_optional_str(state.get("updated_at")),
    )


def build_analysis_state_event(
    state: dict[str, Any],
    event: str | None = None,
) -> AnalysisStateEventDTO:
    project_id = str(state["id"])
    fallback_url = f"/api/analysis/projects/{project_id}"
    status = _optional_str(state.get("status"))
    return AnalysisStateEventDTO(
        event=event or _default_event_name(status),
        resource="retail_project",
        channel=project_channel(project_id),
        resource_id=project_id,
        project_id=project_id,
        job_id=_optional_str(state.get("job_id")),
        trace_id=_optional_str(state.get("trace_id")),
        status=status,
        stage=_event_stage_name(state),
        payload={
            "project_id": project_id,
            "job_id": _optional_str(state.get("job_id")),
            "trace_id": _optional_str(state.get("trace_id")),
            "status": status,
            "stage_statuses": sanitize(state.get("stage_statuses", [])),
            "error": _optional_str(state.get("error")),
            "fallback_url": fallback_url,
        },
        fallback_url=fallback_url,
        occurred_at=_optional_str(state.get("updated_at")),
        retry_ms=3000,
        terminal=status in {"completed", "failed"},
    )


def _dataset_filename(state: dict[str, Any]) -> str | None:
    ref = state.get("dataset_ref")
    if not isinstance(ref, dict):
        return None
    name = ref.get("name")
    return str(name) if name else None


def empty_marketer_insights() -> dict[str, list[dict[str, Any]]]:
    return {key: [] for key in MARKETER_INSIGHT_KEYS}


def collect_result_refs(result: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for attr_name in ("quality_artifact_ref", "artifact_ref", "model_ref"):
        ref = getattr(result, attr_name, None)
        if ref is not None:
            refs.append(public_ref(ref))

    artifact_refs = getattr(result, "artifact_refs", None)
    if isinstance(artifact_refs, dict):
        refs.extend(public_ref(ref) for ref in artifact_refs.values())
    return refs


def public_ref(ref: Any) -> dict[str, Any]:
    if is_dataclass(ref):
        payload = asdict(ref)
    elif isinstance(ref, dict):
        payload = dict(ref)
    else:
        payload = {
            "id": getattr(ref, "id", ""),
            "type": getattr(ref, "type", ""),
            "name": getattr(ref, "name", ""),
            "url": getattr(ref, "url", ""),
            "metadata": getattr(ref, "metadata", {}),
        }
    return {
        "id": sanitize(payload.get("id")),
        "type": sanitize(payload.get("type")),
        "name": sanitize(payload.get("name")),
        "url": sanitize(payload.get("url")),
        "metadata": sanitize(payload.get("metadata") or {}),
    }


def format_recommendations(table: Any) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for row in records_from_table(table):
        source = row.get("主要来源") or row.get("source") or ""
        recommendations.append(
            {
                "customer_id": str(row.get("user_id", "")),
                "item": str(row.get("item_id") or row.get("item") or ""),
                "score": float_or_zero(row.get("score")),
                "reason": str(row.get("reason") or source),
                "score_breakdown": {
                    "source": source,
                    "rank": sanitize(row.get("rank")),
                    "category": sanitize(row.get("cat_l3")),
                },
            }
        )
    return recommendations


def format_marketer_insights(result: Any) -> dict[str, list[dict[str, Any]]]:
    return {
        "segment_value": records_from_table(result.segment_value),
        "promotion_effect": records_from_table(result.promotion_effect_detail),
        "bundle_strategy": records_from_table(result.bundle_strategy),
        "category_strategy": records_from_table(result.category_strategy),
    }


def records_from_table(table: Any) -> list[dict[str, Any]]:
    if table is None:
        return []
    if hasattr(table, "to_dict"):
        records = table.to_dict(orient="records")
    elif isinstance(table, list):
        records = table
    else:
        return []
    return [sanitize(record) for record in records if isinstance(record, dict)]


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize(inner) for key, inner in value.items()}
    if isinstance(value, list | tuple):
        return [sanitize(inner) for inner in value]
    if isinstance(value, str | int | bool) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return sanitize(item())
        except (TypeError, ValueError):
            pass
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def float_or_zero(value: Any) -> float:
    sanitized = sanitize(value)
    try:
        result = float(sanitized)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def _state_payload(
    *,
    project_id: str,
    name: str,
    description: str,
    status: str,
    stage_statuses: list[dict[str, Any]] | list[Any],
    summary: dict[str, Any] | Any,
    dataset_ref: dict[str, Any] | None,
    quality_summary: dict[str, Any] | Any,
    artifact_refs: list[dict[str, Any]] | list[Any],
    recommendations: list[dict[str, Any]] | list[Any],
    marketer_insights: dict[str, Any] | Any,
    run_info: RetailAnalysisRunInfoDTO | dict[str, Any] | None,
    job_id: str | None,
    trace_id: str | None,
    error: str | None,
    created_at: str | None,
    updated_at: str | None,
) -> dict[str, Any]:
    run_info_payload = _run_info_payload(run_info)
    return {
        "id": project_id,
        "name": name,
        "description": description,
        "status": status,
        "stage_statuses": sanitize(stage_statuses),
        "summary": sanitize(summary or {}),
        "dataset_ref": sanitize(dataset_ref) if dataset_ref else None,
        "quality_summary": sanitize(quality_summary or {}),
        "artifact_refs": sanitize(artifact_refs or []),
        "recommendations": sanitize(recommendations or []),
        "marketer_insights": sanitize(marketer_insights or empty_marketer_insights()),
        "run_info": run_info_payload,
        "job_id": run_info_payload.get("job_id") if run_info_payload else _optional_str(job_id),
        "trace_id": (
            run_info_payload.get("trace_id") if run_info_payload else _optional_str(trace_id)
        ),
        "error": _optional_str(error)
        or (run_info_payload.get("error") if run_info_payload else None),
        "created_at": _optional_str(created_at),
        "updated_at": _optional_str(updated_at),
    }


def _run_info_payload(
    run_info: RetailAnalysisRunInfoDTO | dict[str, Any] | None,
) -> dict[str, Any] | None:
    if run_info is None:
        return None
    if is_dataclass(run_info):
        payload = asdict(run_info)
    elif isinstance(run_info, dict):
        payload = dict(run_info)
    else:
        return None

    attempt = payload.get("attempt", 0)
    try:
        normalized_attempt = max(int(attempt), 0)
    except (TypeError, ValueError):
        normalized_attempt = 0

    return {
        "job_id": _optional_str(payload.get("job_id")),
        "trace_id": _optional_str(payload.get("trace_id")),
        "trigger": _optional_str(payload.get("trigger")) or "retail_analysis_api",
        "attempt": normalized_attempt,
        "status": _optional_str(payload.get("status")) or "queued",
        "error": _optional_str(payload.get("error")),
        "created_at": _optional_str(payload.get("created_at")),
        "updated_at": _optional_str(payload.get("updated_at")),
        "metadata": sanitize(payload.get("metadata") or {}),
    }


def _run_info_dto_from_state(state: dict[str, Any]) -> RetailAnalysisRunInfoDTO | None:
    payload = _run_info_payload(state.get("run_info"))
    if payload is None:
        job_id = _optional_str(state.get("job_id"))
        trace_id = _optional_str(state.get("trace_id"))
        if not job_id and not trace_id:
            return None
        payload = {
            "job_id": job_id,
            "trace_id": trace_id,
            "trigger": "retail_analysis_api",
            "attempt": 0,
            "status": _optional_str(state.get("status")) or "queued",
            "error": _optional_str(state.get("error")),
            "created_at": _optional_str(state.get("created_at")),
            "updated_at": _optional_str(state.get("updated_at")),
            "metadata": {},
        }

    if not any(
        [
            payload.get("job_id"),
            payload.get("trace_id"),
            payload.get("error"),
            payload.get("attempt", 0) > 0,
            payload.get("status") not in {None, "queued"},
        ]
    ):
        return None

    return RetailAnalysisRunInfoDTO(
        job_id=payload.get("job_id") or "",
        trace_id=payload.get("trace_id") or "",
        trigger=payload.get("trigger") or "retail_analysis_api",
        attempt=int(payload.get("attempt") or 0),
        status=payload.get("status") or "queued",
        error=payload.get("error"),
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
        metadata=payload.get("metadata") or {},
    )


def _default_event_name(status: str | None) -> str:
    if status == "completed":
        return "completed"
    if status == "failed":
        return "failed"
    return "state_changed"


def _event_stage_name(state: dict[str, Any]) -> str | None:
    stages = state.get("stage_statuses", [])
    if not isinstance(stages, list):
        return None
    for stage in stages:
        if isinstance(stage, dict) and stage.get("status") == "processing":
            return _optional_str(stage.get("stage"))
    for stage in reversed(stages):
        if isinstance(stage, dict) and stage.get("status") == "failed":
            return _optional_str(stage.get("stage"))
    for stage in reversed(stages):
        if not isinstance(stage, dict):
            continue
        if stage.get("status") == "completed" and stage.get("artifact_refs"):
            return _optional_str(stage.get("stage"))
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
