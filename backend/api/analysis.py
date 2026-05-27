"""HTTP boundary for Retail Analysis V2 and Data Processing Analysis resources."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from backend.api.dependencies import (
    get_customer_text_suggestion_pipeline,
    get_data_processing_analysis_flow,
    get_retail_analysis_flow,
)
from backend.api.error_mapping import map_internal_error
from backend.business.flows.data_processing_analysis_flow import DataProcessingAnalysisFlow
from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow
from backend.business.pipelines.customer_text_suggestion_pipeline import (
    CustomerTextSuggestionPipeline,
)
from backend.core.errors import MarketMindError
from backend.providers.analysis_event_stream_provider import job_channel, project_channel
from backend.providers.dtos import AnalysisEventSubscriptionItemDTO

router = APIRouter()


class RetailAnalysisProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Project name is required")
        return stripped


class DataProcessingJobCreate(BaseModel):
    project_id: str = Field(min_length=1)
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Job name is required")
        return stripped


class CustomerSuggestionCreate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    llm_config: dict[str, str | None] = Field(default_factory=dict)


def _success(data: dict) -> dict:
    return {"success": True, "data": data}


def _sse_frame(item: AnalysisEventSubscriptionItemDTO) -> str:
    lines: list[str] = []
    if item.event_id:
        lines.append(f"id: {item.event_id}")
    lines.append(f"event: {item.event}")
    if item.retry_ms is not None:
        lines.append(f"retry: {item.retry_ms}")
    payload = json.dumps(asdict(item), ensure_ascii=False, separators=(",", ":"))
    lines.append(f"data: {payload}")
    return "\n".join(lines) + "\n\n"


def _retail_project_snapshot(project: dict[str, Any]) -> AnalysisEventSubscriptionItemDTO:
    project_id = str(project["id"])
    fallback_url = f"/api/analysis/projects/{project_id}"
    return AnalysisEventSubscriptionItemDTO(
        event_id="snapshot",
        event="state_changed",
        resource="retail_project",
        channel=project_channel(project_id),
        resource_id=project_id,
        project_id=project_id,
        job_id=project.get("job_id"),
        trace_id=project.get("trace_id"),
        status=project.get("status"),
        payload={
            "project_id": project_id,
            "status": project.get("status"),
            "stage_statuses": project.get("stage_statuses") or [],
            "fallback_url": fallback_url,
        },
        fallback_url=fallback_url,
        occurred_at=project.get("updated_at"),
        retry_ms=3000,
        terminal=project.get("status") in {"completed", "failed", "已完成", "失败"},
    )


def _data_processing_job_snapshot(
    project_id: str,
    job_id: str,
    job: dict[str, Any],
) -> AnalysisEventSubscriptionItemDTO:
    fallback_url = f"/api/analysis/jobs/{job_id}?project_id={project_id}"
    return AnalysisEventSubscriptionItemDTO(
        event_id="snapshot",
        event="state_changed",
        resource="data_processing_job",
        channel=job_channel(job_id),
        resource_id=job_id,
        project_id=project_id,
        job_id=job_id,
        status=job.get("status"),
        payload={
            "project_id": project_id,
            "job_id": job_id,
            "status": job.get("status"),
            "stage_statuses": job.get("stages") or [],
            "outputs_ready": bool(job.get("output_refs")),
            "fallback_url": fallback_url,
        },
        fallback_url=fallback_url,
        occurred_at=job.get("updated_at"),
        retry_ms=3000,
        terminal=job.get("status") in {"completed", "failed"},
    )


@router.post("/customer-suggestions")
async def generate_customer_suggestion(
    payload: CustomerSuggestionCreate,
    pipeline: CustomerTextSuggestionPipeline = Depends(get_customer_text_suggestion_pipeline),
) -> dict:
    try:
        return await pipeline.generate(payload.data, payload.llm_config)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc


# ---------- Retail V2 (legacy) ----------


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: RetailAnalysisProjectCreate,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        project = flow.create_project(payload.name, payload.description)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(project)


@router.get("/projects")
async def list_projects(
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.list_projects()
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.delete_project(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.post("/projects/{project_id}/dataset")
async def upload_dataset(
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.upload_dataset(
            project_id,
            file.filename or "",
            await file.read(),
        )
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.post("/projects/{project_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_analysis(
    project_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.start_analysis(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        project = flow.get_project(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(project)


@router.get("/projects/{project_id}/events")
async def stream_project_events(
    project_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    try:
        project = flow.get_project(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc

    def event_frames() -> Iterator[str]:
        yield _sse_frame(_retail_project_snapshot(project))
        for item in flow.providers.analysis_event_stream.subscribe_project_events(
            project_id,
            last_event_id,
        ):
            yield _sse_frame(item)

    return StreamingResponse(event_frames(), media_type="text/event-stream")


@router.get("/projects/{project_id}/artifacts")
async def list_artifacts(
    project_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.list_artifacts(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/projects/{project_id}/datasets/{dataset_id}")
async def get_dataset_ref(
    project_id: str,
    dataset_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.get_dataset_ref(project_id, dataset_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/projects/{project_id}/artifacts/{artifact_id:path}/payload")
async def get_artifact_payload(
    project_id: str,
    artifact_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.get_artifact_payload(project_id, artifact_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/projects/{project_id}/artifacts/{artifact_id:path}")
async def get_artifact_ref(
    project_id: str,
    artifact_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.get_artifact_ref(project_id, artifact_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/projects/{project_id}/models/{model_type}/{version}")
async def get_model_ref(
    project_id: str,
    model_type: str,
    version: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.get_model_ref(project_id, model_type, version)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/projects/{project_id}/recommendations")
async def list_recommendations(
    project_id: str,
    customer_id: str | None = None,
    top_k: int = Query(default=10, ge=1, le=100),
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.list_recommendations(project_id, customer_id=customer_id, top_k=top_k)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/projects/{project_id}/marketer-insights")
async def get_marketer_insights(
    project_id: str,
    flow: RetailAnalysisFlow = Depends(get_retail_analysis_flow),
) -> dict:
    try:
        result = flow.get_marketer_insights(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


# ---------- Data Processing (chain-native) ----------


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_data_processing_job(
    payload: DataProcessingJobCreate,
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
) -> dict:
    try:
        result = flow.create_job(payload.project_id, payload.name)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.post("/jobs/{job_id}/raw-dataset")
async def upload_raw_dataset(
    job_id: str,
    project_id: str,
    file: Annotated[UploadFile, File(...)],
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
) -> dict:
    try:
        result = flow.upload_raw_dataset(project_id, job_id, file.filename or "", await file.read())
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.post("/jobs/{job_id}/regularize")
async def regularize_dataset(
    job_id: str,
    project_id: str,
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
) -> dict:
    try:
        result = flow.regularize(project_id, job_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.post("/jobs/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_data_processing_analysis(
    job_id: str,
    project_id: str,
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
) -> dict:
    try:
        result = flow.run_analysis(project_id, job_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/jobs/{job_id}")
async def get_data_processing_job(
    job_id: str,
    project_id: str,
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
) -> dict:
    try:
        result = flow.get_job(project_id, job_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/jobs/{job_id}/events")
async def stream_data_processing_job_events(
    job_id: str,
    project_id: str,
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    try:
        job = flow.get_job(project_id, job_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc

    def event_frames() -> Iterator[str]:
        yield _sse_frame(_data_processing_job_snapshot(project_id, job_id, job))
        for item in flow.providers.analysis_event_stream.subscribe_job_events(
            job_id, last_event_id
        ):
            yield _sse_frame(item)

    return StreamingResponse(event_frames(), media_type="text/event-stream")


@router.get("/jobs/{job_id}/outputs")
async def list_data_processing_outputs(
    job_id: str,
    project_id: str,
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
) -> dict:
    try:
        result = flow.list_outputs(project_id, job_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/jobs/{job_id}/datasets/{dataset_id}")
async def get_data_processing_dataset(
    job_id: str,
    dataset_id: str,
    project_id: str,
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
) -> dict:
    try:
        result = flow.get_dataset_ref(project_id, job_id, dataset_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)


@router.get("/jobs/{job_id}/sidecars/{sidecar_id:path}")
async def get_data_processing_sidecar(
    job_id: str,
    sidecar_id: str,
    project_id: str,
    flow: DataProcessingAnalysisFlow = Depends(get_data_processing_analysis_flow),
) -> dict:
    try:
        result = flow.load_sidecar(project_id, job_id, sidecar_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return _success(result)
