"""HTTP boundary for project resources.

Each handler only parses the request, delegates to a pipeline/flow,
maps the response, and maps internal errors at the boundary.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from backend.api.dependencies import (
    get_dataset_upload_pipeline,
    get_project_customer_pipeline,
    get_project_pipeline,
    get_project_recommendation_pipeline,
)
from backend.api.error_mapping import map_internal_error
from backend.business.pipelines.dataset_upload_pipeline import (
    DatasetUploadPipeline,
)
from backend.business.pipelines.dataset_upload_pipeline import (
    UploadedFile as PipelineUploadedFile,
)
from backend.business.pipelines.project_pipeline import ProjectPipeline
from backend.business.pipelines.project_read_pipelines import (
    ProjectCustomerPipeline,
    ProjectRecommendationPipeline,
)
from backend.core.errors import MarketMindError
from backend.models.project import (
    AnalysisParameters,
    Project,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter()


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    pipeline: ProjectPipeline = Depends(get_project_pipeline),
) -> ProjectResponse:
    """Create a project without dataset."""

    payload = ProjectCreate(
        name=project_data.name,
        description=project_data.description,
        parameters=project_data.parameters or AnalysisParameters(),
    )
    try:
        created = pipeline.create(payload)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return ProjectResponse(success=True, message="项目创建成功", data=created)


@router.post("/{project_id}/upload/")
async def upload_dataset(
    project_id: str,
    file: UploadFile = File(...),
    pipeline: DatasetUploadPipeline = Depends(get_dataset_upload_pipeline),
) -> dict:
    """Upload a dataset and trigger background analysis."""

    try:
        pipeline.upload(
            project_id,
            PipelineUploadedFile(filename=file.filename or "", stream=file.file),
        )
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return {
        "success": True,
        "message": "文件上传成功，开始分析",
        "project_id": project_id,
    }


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    pipeline: ProjectPipeline = Depends(get_project_pipeline),
) -> ProjectListResponse:
    """List projects ordered by the repository default."""

    try:
        items, total = pipeline.list(skip=skip, limit=limit)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return ProjectListResponse(success=True, message="获取项目列表成功", total=total, data=items)


@router.get("/{project_id}/", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    pipeline: ProjectPipeline = Depends(get_project_pipeline),
) -> ProjectResponse:
    """Return a single project by id."""

    try:
        project = pipeline.get(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return ProjectResponse(success=True, message="获取项目详情成功", data=project)


@router.put("/{project_id}/", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    updates: ProjectUpdate,
    pipeline: ProjectPipeline = Depends(get_project_pipeline),
) -> ProjectResponse:
    """Update mutable project fields."""

    try:
        project = pipeline.update(project_id, updates)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return ProjectResponse(success=True, message="更新项目成功", data=project)


@router.delete("/{project_id}/")
async def delete_project(
    project_id: str,
    pipeline: ProjectPipeline = Depends(get_project_pipeline),
) -> dict:
    """Delete a project and its workspace files."""

    try:
        pipeline.delete(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "message": "删除项目成功"}


@router.post("/{project_id}/reanalyze/")
async def reanalyze_project(
    project_id: str,
    pipeline: DatasetUploadPipeline = Depends(get_dataset_upload_pipeline),
) -> dict:
    """Schedule reanalysis on an existing dataset."""

    try:
        pipeline.reanalyze(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "message": "重新分析任务已启动"}


@router.get("/{project_id}/download/report/")
async def download_report(
    project_id: str,
    pipeline: ProjectPipeline = Depends(get_project_pipeline),
) -> FileResponse:
    """Stream the generated Markdown report."""

    try:
        path, filename = pipeline.resolve_report(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return FileResponse(path=path, filename=filename, media_type="text/markdown")


@router.get("/{project_id}/customers/")
async def get_project_customers(
    project_id: str,
    cluster_id: Optional[int] = Query(None, description="按聚类ID过滤"),
    pipeline: ProjectCustomerPipeline = Depends(get_project_customer_pipeline),
) -> dict:
    """List normalized customer rows for a project."""

    try:
        customers = pipeline.list(project_id, cluster_id=cluster_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return {"success": True, "data": customers}


@router.get("/{project_id}/audio/")
async def get_audio_file(
    project_id: str,
    pipeline: ProjectPipeline = Depends(get_project_pipeline),
) -> FileResponse:
    """Stream the generated project audio."""

    try:
        path, filename = pipeline.resolve_audio(project_id)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return FileResponse(path=path, filename=filename, media_type="audio/mpeg")


@router.get("/{project_id}/recommend/")
async def recommend_item(
    project_id: str,
    item: str = Query(..., description="商品名称，如：椅子"),
    project_pipeline: ProjectPipeline = Depends(get_project_pipeline),
    pipeline: ProjectRecommendationPipeline = Depends(get_project_recommendation_pipeline),
) -> dict:
    """Return per-item relations using the project dataset."""

    try:
        project: Project = project_pipeline.get(project_id)
        result = pipeline.recommend_for_item(project_id, item=item)
    except MarketMindError as exc:
        raise map_internal_error(exc) from exc
    return {**result, "dataset_path": project.dataset_path}
