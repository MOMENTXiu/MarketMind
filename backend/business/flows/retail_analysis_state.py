"""Retail Analysis V2 state shaping helpers."""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from typing import Any

MARKETER_INSIGHT_KEYS = (
    "segment_value",
    "promotion_effect",
    "bundle_strategy",
    "category_strategy",
)


def new_stage(stage_name: str) -> dict[str, Any]:
    return {"stage": stage_name, "status": "queued", "error": None, "artifact_refs": []}


def project_view(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": state["id"],
        "name": state["name"],
        "description": state.get("description", ""),
        "status": state["status"],
        "dataset_ref": public_ref(state["dataset_ref"]) if state.get("dataset_ref") else None,
        "dataset_filename": _dataset_filename(state),
        "quality_summary": sanitize(state.get("quality_summary", {})),
        "artifact_refs": [public_ref(ref) for ref in state.get("artifact_refs", [])],
        "recommendations": sanitize(state.get("recommendations", [])),
        "marketer_insights": sanitize(state.get("marketer_insights", empty_marketer_insights())),
        "stage_statuses": list(state.get("stage_statuses", [])),
        "summary": dict(state.get("summary", {})),
        "job_id": state.get("job_id"),
        "trace_id": state.get("trace_id"),
        "error": state.get("error"),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
    }


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
