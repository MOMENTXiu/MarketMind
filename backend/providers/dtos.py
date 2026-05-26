"""Shared DTOs for provider boundary contracts."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderErrorDTO:
    code: str
    message: str
    provider: str | None = None
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResultDTO:
    success: bool
    error: ProviderErrorDTO | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UploadedFileDTO:
    filename: str
    content_type: str | None
    size_bytes: int | None = None


@dataclass(frozen=True)
class AssetReferenceDTO:
    path: Path
    url: str | None = None
    media_type: str | None = None
    exists: bool = True


@dataclass(frozen=True)
class DatasetReferenceDTO:
    project_id: str | None
    path: Path
    filename: str | None = None


RETAIL_RAW_SALES_COLUMNS: tuple[str, ...] = (
    "顾客编号",
    "大类编码",
    "大类名称",
    "中类编码",
    "中类名称",
    "小类编码",
    "小类名称",
    "销售日期",
    "销售月份",
    "商品编码",
    "规格型号",
    "商品类型",
    "单位",
    "销售数量",
    "销售金额",
    "商品单价",
    "是否促销",
)


@dataclass(frozen=True)
class RetailDatasetReferenceDTO:
    id: str
    project_id: str
    type: str
    name: str
    storage_key: str
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass(frozen=True)
class AnalysisArtifactReferenceDTO:
    id: str
    project_id: str
    type: str
    name: str
    url: str
    storage_key: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass(frozen=True)
class AnalysisModelReferenceDTO:
    id: str
    project_id: str
    type: str
    name: str
    model_type: str
    version: str
    url: str
    storage_key: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass(frozen=True)
class SpeechSynthesisRequestDTO:
    text: str
    output_path: Path
    voice: str | None = None
    rate: str | None = None
    volume: str | None = None


@dataclass(frozen=True)
class SpeechSynthesisResultDTO:
    audio_path: Path
    audio_url: str | None = None
    duration_seconds: float | None = None


@dataclass(frozen=True)
class LLMMessageDTO:
    role: str
    content: str


@dataclass(frozen=True)
class LLMRequestDTO:
    provider: str
    base_url: str
    model: str
    messages: list[LLMMessageDTO]
    api_key: str | None = None
    timeout_seconds: float = 30.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponseDTO:
    text: str
    provider: str
    model: str | None = None
    raw_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelArtifactDTO:
    path: Path
    payload: Any


@dataclass(frozen=True)
class AnalysisJobDTO:
    project_id: str
    trigger: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RegularizedDatasetReferenceDTO:
    id: str
    project_id: str
    job_id: str
    type: str
    name: str
    storage_key: str
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass(frozen=True)
class RegularizationSidecarReferenceDTO:
    id: str
    project_id: str
    job_id: str
    sidecar_type: str
    name: str
    storage_key: str
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass(frozen=True)
class RegularizationCapabilityDTO:
    can_run_sales_stats: bool
    can_run_time_trend: bool
    can_run_customer_profile: bool
    can_run_association: bool
    can_run_recommendation: bool
    can_run_forecast: bool
    can_run_promotion_analysis: bool
    can_run_profit_analysis: bool
    can_run_price_sensitivity: bool
    can_run_discount_analysis: bool
    degraded_fields: dict[str, str] = field(default_factory=dict)
    capability_zh: dict[str, bool] = field(default_factory=dict)
    runnable_count: int = 0


@dataclass(frozen=True)
class RegularizationQualityDTO:
    raw_rows: int
    normalized_rows: int
    duplicate_rows_removed: int
    mapped_field_count: int
    available_standard_fields: list[str] = field(default_factory=list)
    missing_rates: dict[str, float | None] = field(default_factory=dict)
    invalid_date_count: int | None = None
    invalid_amount_count: int | None = None
    invalid_user_id_count: int | None = None
    return_rows: int = 0
    scores: dict[str, float] = field(default_factory=dict)
    analysis_ready_score: float = 0.0
    grade: str = ""


@dataclass(frozen=True)
class DataProcessingJobStateDTO:
    job_id: str
    project_id: str
    status: str
    stages: list[dict[str, Any]] = field(default_factory=list)
    quality: dict[str, Any] | None = None
    capability: dict[str, Any] | None = None
    output_refs: list[dict[str, Any]] = field(default_factory=list)
    skipped_reasons: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
