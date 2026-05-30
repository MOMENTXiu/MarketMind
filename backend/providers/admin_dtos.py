"""Admin Console DTOs for provider boundary contracts.

All admin backend layers pass these DTOs; no DB models or SDK responses
cross the provider boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ── Health / Status ───────────────────────────────────────────────────────────

ServiceStatus = Literal["healthy", "degraded", "down", "unknown"]
ServiceCategory = Literal["app", "infra", "external"]


@dataclass(frozen=True)
class ServiceHealthDTO:
    key: str
    name: str
    category: ServiceCategory
    status: ServiceStatus
    latency_ms: float | None = None
    checked_at: str | None = None
    message: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class AdminHealthSummaryDTO:
    overall_status: ServiceStatus
    services: list[ServiceHealthDTO] = field(default_factory=list)
    generated_at: str | None = None


# ── Settings ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LlmSettingsDTO:
    provider: str
    base_url: str | None = None
    model: str | None = None
    api_key_configured: bool = False
    timeout_seconds: int | None = None
    enabled: bool = False


@dataclass(frozen=True)
class InfraComponentSettingsDTO:
    host: str
    port: int
    database: str | None = None
    username: str | None = None
    password_configured: bool = False


@dataclass(frozen=True)
class MinioSettingsDTO:
    endpoint: str
    bucket: str
    access_key_configured: bool = False
    secret_key_configured: bool = False
    secure: bool = False


@dataclass(frozen=True)
class InfraSettingsDTO:
    postgres: InfraComponentSettingsDTO | None = None
    redis: InfraComponentSettingsDTO | None = None
    minio: MinioSettingsDTO | None = None


AlertLevel = Literal["error", "warning", "critical"]


@dataclass(frozen=True)
class AlertSettingsDTO:
    enabled: bool = False
    server_url: str | None = None
    device_key_configured: bool = False
    default_group: str | None = None
    alert_levels: list[AlertLevel] = field(default_factory=list)


@dataclass(frozen=True)
class AllSettingsDTO:
    llm: LlmSettingsDTO | None = None
    infra: InfraSettingsDTO | None = None
    alert: AlertSettingsDTO | None = None


@dataclass(frozen=True)
class TestResultDTO:
    success: bool
    message: str
    latency_ms: float | None = None
    detail: dict[str, Any] | None = None


# ── Telemetry / Logs ──────────────────────────────────────────────────────────

EventKind = Literal["debug", "audit", "error", "span"]
LogLevel = Literal["info", "warning", "error", "critical"]


@dataclass(frozen=True)
class TelemetryEnvelopeDTO:
    id: str
    kind: EventKind
    level: LogLevel
    event_type: str
    message: str
    actor_user_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    project_id: str | None = None
    job_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdminLogRecordDTO:
    id: str
    level: LogLevel
    event_type: str
    message: str
    actor_user_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    project_id: str | None = None
    job_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class AdminLogQueryDTO:
    kind: EventKind | None = None
    level: LogLevel | None = None
    event_type: str | None = None
    actor_user_id: str | None = None
    project_id: str | None = None
    job_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True)
class AdminLogPageDTO:
    items: list[AdminLogRecordDTO] = field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True)
class ExportResultDTO:
    content: str
    format: str  # "json" or "csv"
    filename: str | None = None
    record_count: int = 0


# ── Users ─────────────────────────────────────────────────────────────────────

UserRole = Literal["user", "admin"]
UserStatus = Literal["active", "disabled"]


@dataclass(frozen=True)
class AdminUserListItemDTO:
    id: str
    email: str
    display_name: str | None = None
    role: UserRole = "user"
    status: UserStatus = "active"
    project_count: int = 0
    last_login_at: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class AdminUserProjectDTO:
    id: str
    name: str
    status: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class AdminUserDetailDTO:
    id: str
    email: str
    display_name: str | None = None
    role: UserRole = "user"
    status: UserStatus = "active"
    project_count: int = 0
    projects: list[AdminUserProjectDTO] = field(default_factory=list)
    last_login_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class UpdateRoleDTO:
    role: UserRole


@dataclass(frozen=True)
class UpdateStatusDTO:
    status: UserStatus


# ── Settings Edit ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SettingsEditDTO:
    """A single key=value edit for .env file."""

    key: str
    value: str | None = None  # None = delete line or preserve sensitive
    is_sensitive: bool = False


@dataclass(frozen=True)
class EnvSettingsUpdateDTO:
    """Batch update for .env settings."""

    updates: list[SettingsEditDTO] = field(default_factory=list)


@dataclass(frozen=True)
class EnvFileInfoDTO:
    """Read-only info about the .env file."""

    path: str
    keys: dict[str, str] = field(default_factory=dict)


# ── LLM Multi-Model Config ───────────────────────────────────────────────────


@dataclass(frozen=True)
class LlmConfigItemDTO:
    id: str
    name: str
    provider: str  # "openai" | "anthropic" | "deepseek" | "custom"
    base_url: str | None = None
    api_key_configured: bool = False
    model: str | None = None
    timeout_seconds: int = 30
    is_active: bool = False
    created_at: str | None = None


@dataclass(frozen=True)
class LlmConfigListDTO:
    configs: list[LlmConfigItemDTO] = field(default_factory=list)


@dataclass(frozen=True)
class LlmConfigSaveDTO:
    """Input DTO for creating/updating an LLM config."""

    name: str
    provider: str
    base_url: str | None = None
    api_key: str | None = None  # plaintext input; adapter masks before storing
    model: str | None = None
    timeout_seconds: int = 30
    is_active: bool = False
