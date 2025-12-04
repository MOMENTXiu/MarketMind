"""
项目数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
import uuid


class ProjectStatus(str, Enum):
    """项目状态枚举"""
    PENDING = "待处理"
    PROCESSING = "处理中"
    COMPLETED = "已完成"
    FAILED = "失败"


class AnalysisParameters(BaseModel):
    """分析参数"""
    min_support: float = Field(0.02, ge=0.0, le=1.0, description="最小支持度")
    min_confidence: float = Field(0.3, ge=0.0, le=1.0, description="最小置信度")
    min_lift: float = Field(1.0, ge=0.0, description="最小提升度")
    forecast_weeks: int = Field(13, ge=1, le=52, description="预测周数")
    n_clusters: int = Field(4, ge=2, le=10, description="聚类数量")


class AnalysisResults(BaseModel):
    """分析结果"""
    association_rules: Optional[List[Dict[str, Any]]] = None
    prediction_data: Optional[Dict[str, Any]] = None
    clustering_data: Optional[Dict[str, Any]] = None
    charts: Optional[Dict[str, str]] = None  # 图表路径
    audio_path: Optional[str] = None  # 语音文件路径
    report_path: Optional[str] = None  # 报告路径


class Project(BaseModel):
    """项目模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="项目ID")
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(None, max_length=500, description="项目描述")
    dataset_filename: Optional[str] = Field(None, description="数据集文件名")
    dataset_path: Optional[str] = Field(None, description="数据集路径")
    status: ProjectStatus = Field(ProjectStatus.PENDING, description="项目状态")
    parameters: AnalysisParameters = Field(default_factory=AnalysisParameters, description="分析参数")
    results: Optional[AnalysisResults] = Field(None, description="分析结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(None, max_length=500, description="项目描述")
    parameters: Optional[AnalysisParameters] = None


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    parameters: Optional[AnalysisParameters] = None


class ProjectResponse(BaseModel):
    """项目响应"""
    success: bool
    message: str
    data: Optional[Project] = None


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    success: bool
    message: str
    total: int
    data: List[Project]
