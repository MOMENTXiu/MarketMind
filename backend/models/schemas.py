"""
Pydantic 数据模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============ 关联规则模块 ============
class AssociationRuleRequest(BaseModel):
    """关联规则分析请求"""

    min_support: float = Field(0.02, ge=0.0, le=1.0, description="最小支持度")
    min_confidence: float = Field(0.3, ge=0.0, le=1.0, description="最小置信度")
    min_lift: float = Field(1.0, ge=0.0, description="最小提升度")
    top_n: int = Field(10, ge=1, le=100, description="返回Top N规则")


class AssociationRule(BaseModel):
    """单条关联规则"""

    antecedents: List[str] = Field(..., description="前项商品")
    consequent: str = Field(..., description="后项商品")
    support: float = Field(..., description="支持度")
    confidence: float = Field(..., description="置信度")
    lift: float = Field(..., description="提升度")
    strategy: str = Field(..., description="营销策略建议")


class AssociationRuleResponse(BaseModel):
    """关联规则分析响应"""

    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    rules: List[AssociationRule] = Field(default_factory=list)
    charts: Dict[str, str] = Field(default_factory=dict, description="图表URL")


# ============ 销售预测模块 ============
class PredictionRequest(BaseModel):
    """销售预测请求"""

    forecast_weeks: int = Field(13, ge=1, le=52, description="预测周数")
    model_type: str = Field("ridge", description="模型类型: ridge/random_forest/gradient_boosting")


class WeeklyForecast(BaseModel):
    """单周预测"""

    week: int
    date: str
    sales: float
    profit: float
    profit_rate: float


class PredictionResponse(BaseModel):
    """销售预测响应"""

    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    forecasts: List[WeeklyForecast] = Field(default_factory=list)
    model_performance: Dict[str, float] = Field(default_factory=dict)
    charts: Dict[str, str] = Field(default_factory=dict)


# ============ 客户聚类模块 ============
class ClusteringRequest(BaseModel):
    """客户聚类请求"""

    n_clusters: int = Field(4, ge=2, le=10, description="聚类数量")
    method: str = Field("kmeans", description="聚类方法: kmeans/hierarchical")


class CustomerCluster(BaseModel):
    """客户群体"""

    cluster_id: int
    name: str
    customer_count: int
    avg_recency: float
    avg_frequency: float
    avg_monetary: float
    sales_contribution: float
    profit_contribution: float
    marketing_strategy: str


class ClusteringResponse(BaseModel):
    """客户聚类响应"""

    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    clusters: List[CustomerCluster] = Field(default_factory=list)
    charts: Dict[str, str] = Field(default_factory=dict)


# ============ 语音播报模块 ============
class VoiceRequest(BaseModel):
    """语音生成请求"""

    text: Optional[str] = Field(None, description="自定义文本，为空则自动生成")
    voice: str = Field("zh-CN-YunxiNeural", description="语音角色")
    include_modules: List[str] = Field(
        default_factory=lambda: ["association", "prediction", "clustering"],
        description="包含的模块",
    )


class VoiceResponse(BaseModel):
    """语音生成响应"""

    success: bool
    message: str
    text: str
    audio_url: str
    duration: Optional[float] = None


# ============ 通用响应 ============
class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    service: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """错误响应"""

    success: bool = False
    message: str
    detail: Optional[str] = None
