"""State helpers for DataProcessingAnalysisFlow."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from backend.providers.analysis_event_stream_provider import job_channel
from backend.providers.dtos import AnalysisStateEventDTO

PROJECT_STATUSES = {"queued", "processing", "completed", "failed", "needs_review"}
STAGE_STATUSES = {"queued", "processing", "completed", "skipped", "failed", "needs_review"}
STAGE_NAMES = (
    "dataset_regularization",
    "overview",
    "profile_segmentation",
    "association",
    "recommendation",
    "promotion",
    "summary",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def new_job_state(project_id: str, name: str) -> dict[str, Any]:
    job_id = uuid4().hex
    return {
        "job_id": job_id,
        "project_id": project_id,
        "name": name,
        "status": "queued",
        "stages": [new_stage(s) for s in STAGE_NAMES],
        "quality": None,
        "capability": None,
        "output_refs": [],
        "skipped_reasons": {},
        "error": None,
        "created_at": _now(),
        "updated_at": _now(),
    }


def new_stage(stage_name: str) -> dict[str, Any]:
    return {
        "stage": stage_name,
        "status": "queued",
        "error": None,
        "artifact_refs": [],
    }


def job_view(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": state["job_id"],
        "project_id": state["project_id"],
        "name": state["name"],
        "status": state["status"],
        "stages": state["stages"],
        "quality": state.get("quality"),
        "capability": state.get("capability"),
        "output_refs": state.get("output_refs", []),
        "skipped_reasons": state.get("skipped_reasons", {}),
        "error": state.get("error"),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
    }


def build_data_processing_state_event(
    state: dict[str, Any],
    event: str | None = None,
) -> AnalysisStateEventDTO:
    job_id = str(state["job_id"])
    project_id = str(state["project_id"])
    fallback_url = f"/api/analysis/jobs/{job_id}?project_id={project_id}"
    status = str(state.get("status") or "queued")
    return AnalysisStateEventDTO(
        event=event or _default_event_name(status),
        resource="data_processing_job",
        channel=job_channel(job_id),
        resource_id=job_id,
        project_id=project_id,
        job_id=job_id,
        status=status,
        stage=_event_stage_name(state),
        payload={
            "project_id": project_id,
            "job_id": job_id,
            "status": status,
            "stages": state.get("stages", []),
            "outputs_ready": bool(state.get("output_refs")),
            "fallback_url": fallback_url,
        },
        fallback_url=fallback_url,
        occurred_at=str(state.get("updated_at") or ""),
        retry_ms=3000,
        terminal=status in {"completed", "failed", "needs_review"},
    )


def set_stage(
    state: dict[str, Any],
    stage_name: str,
    status: str,
    error: str | None = None,
    artifact_refs: list[dict[str, Any]] | None = None,
) -> None:
    if status not in STAGE_STATUSES:
        raise ValueError(f"Invalid stage status: {status}")
    for stage in state["stages"]:
        if stage["stage"] != stage_name:
            continue
        stage["status"] = status
        stage["error"] = error
        if artifact_refs is not None:
            stage["artifact_refs"] = artifact_refs
        return
    raise ValueError(f"Unknown stage: {stage_name}")


def append_output_refs(state: dict[str, Any], refs: list[dict[str, Any]]) -> None:
    outputs = list(state.get("output_refs", []))
    seen = {ref.get("id") for ref in outputs}
    for ref in refs:
        if ref.get("id") in seen:
            continue
        outputs.append(ref)
        seen.add(ref.get("id"))
    state["output_refs"] = outputs


def _default_event_name(status: str | None) -> str:
    if status in {"completed", "failed", "needs_review"}:
        return status
    return "state_changed"


def _event_stage_name(state: dict[str, Any]) -> str | None:
    for stage in state.get("stages", []):
        if stage.get("status") == "processing":
            return str(stage.get("stage"))
    return None
