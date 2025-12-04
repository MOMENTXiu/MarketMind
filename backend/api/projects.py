"""
项目管理 API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import FileResponse
from typing import Optional
import shutil
from pathlib import Path

from backend.models.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectStatus,
    AnalysisParameters
)
from backend.core.storage import storage
from backend.services.analysis_service import run_project_analysis
from backend.core.recommend import query_item_relations

router = APIRouter()


@router.post("/", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate):
    """创建新项目（不含数据集）"""
    try:
        project = Project(
            name=project_data.name,
            description=project_data.description,
            parameters=project_data.parameters or AnalysisParameters(),
            status=ProjectStatus.PENDING
        )
        created_project = storage.create_project(project)
        return ProjectResponse(
            success=True,
            message="项目创建成功",
            data=created_project
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.post("/{project_id}/upload")
async def upload_dataset(
    project_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """上传数据集并开始分析"""
    try:
        # 获取项目
        project = storage.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 验证文件类型
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="仅支持 CSV 和 Excel 文件")

        # 保存文件
        project_dir = storage.get_project_dir(project_id)
        dataset_path = project_dir / "dataset.csv"

        with open(dataset_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)

        # 更新项目信息
        storage.update_project(project_id, {
            'dataset_filename': file.filename,
            'dataset_path': str(dataset_path),
            'status': ProjectStatus.PROCESSING
        })

        # 后台执行分析任务
        if background_tasks:
            background_tasks.add_task(run_project_analysis, project_id)

        return {
            "success": True,
            "message": "文件上传成功，开始分析",
            "project_id": project_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/", response_model=ProjectListResponse)
async def list_projects(skip: int = 0, limit: int = 100):
    """获取项目列表"""
    try:
        projects = storage.list_projects(skip=skip, limit=limit)
        total = storage.count_projects()
        return ProjectListResponse(
            success=True,
            message="获取项目列表成功",
            total=total,
            data=projects
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """获取项目详情"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return ProjectResponse(
        success=True,
        message="获取项目详情成功",
        data=project
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, updates: ProjectUpdate):
    """更新项目信息"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    updated_project = storage.update_project(
        project_id,
        updates.model_dump(exclude_none=True)
    )

    return ProjectResponse(
        success=True,
        message="更新项目成功",
        data=updated_project
    )


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    success = storage.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")

    return {
        "success": True,
        "message": "删除项目成功"
    }


@router.post("/{project_id}/reanalyze")
async def reanalyze_project(project_id: str, background_tasks: BackgroundTasks):
    """重新分析项目"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not project.dataset_path:
        raise HTTPException(status_code=400, detail="项目未上传数据集")

    # 更新状态为处理中
    storage.update_project(project_id, {'status': ProjectStatus.PROCESSING})

    # 后台执行分析
    background_tasks.add_task(run_project_analysis, project_id)

    return {
        "success": True,
        "message": "重新分析任务已启动"
    }


@router.get("/{project_id}/download/report")
async def download_report(project_id: str):
    """下载分析报告"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not project.results or not project.results.report_path:
        raise HTTPException(status_code=404, detail="报告文件不存在")

    report_path = Path(project.results.report_path)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    return FileResponse(
        path=report_path,
        filename=f"{project.name}_分析报告.md",
        media_type="text/markdown"
    )


@router.get("/{project_id}/audio")
async def get_audio_file(project_id: str):
    """获取语音文件"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not project.results or not project.results.audio_path:
        raise HTTPException(status_code=404, detail="语音文件不存在")

    audio_path = Path(project.results.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="语音文件不存在")

    return FileResponse(
        path=audio_path,
        filename=f"{project.name}_播报.mp3",
        media_type="audio/mpeg"
    )


@router.get("/{project_id}/recommend")
async def recommend_item(project_id: str, item: str = Query(..., description="商品名称，如：椅子")):
    """
    根据商品名称，返回与该商品相关的前项 / 后项关联规则。
    暂时忽略 project_id，直接使用全局规则 DataFrame。
    如需按项目区分，可在 load_rules 中扩展按 project_id 读取。
    """
    result = query_item_relations(item)
    return result
