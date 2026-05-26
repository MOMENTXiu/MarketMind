"""HTTP boundary for Retail Analysis V2 and Data Processing Analysis resources."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel, Field, field_validator

from backend.api.dependencies import (
    get_data_processing_analysis_flow,
    get_retail_analysis_flow,
)
from backend.api.error_mapping import map_internal_error
from backend.business.flows.data_processing_analysis_flow import DataProcessingAnalysisFlow
from backend.business.flows.retail_analysis_flow import RetailAnalysisFlow
from backend.core.errors import MarketMindError

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


def _success(data: dict) -> dict:
    return {"success": True, "data": data}


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
