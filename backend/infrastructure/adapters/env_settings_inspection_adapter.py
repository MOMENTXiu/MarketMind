"""Environment-variable-based settings inspection adapter.

Reads Settings from backend.core.config and returns redacted DTOs.
Sensitive fields (API keys, passwords, device keys) are only exposed
as configured/not-configured booleans.
"""

from __future__ import annotations

from backend.core.config import Settings
from backend.providers.admin_dtos import (
    AlertSettingsDTO,
    AllSettingsDTO,
    InfraComponentSettingsDTO,
    InfraSettingsDTO,
    LlmSettingsDTO,
    MinioSettingsDTO,
)
from backend.providers.settings_inspection_provider import SettingsInspectionProvider


def _mask_bool(value: str | None) -> bool:
    """Return True if a non-empty value is configured."""
    return bool(value and value.strip())


class EnvSettingsInspectionAdapter(SettingsInspectionProvider):
    """Read system configuration from the Settings object, redacting secrets."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_llm_settings(self) -> LlmSettingsDTO:
        return LlmSettingsDTO(
            provider=self._settings.LLM_PROVIDER or "openai",
            base_url=self._settings.LLM_BASE_URL if self._settings.LLM_BASE_URL else None,
            model=self._settings.LLM_MODEL if self._settings.LLM_MODEL else None,
            api_key_configured=_mask_bool(self._settings.LLM_API_KEY),
            timeout_seconds=self._settings.LLM_TIMEOUT_SECONDS,
            enabled=self._settings.LLM_PROVIDER is not None,
        )

    def get_infra_settings(self) -> InfraSettingsDTO:
        return InfraSettingsDTO(
            postgres=self._build_pg_settings(),
            redis=self._build_redis_settings(),
            minio=self._build_minio_settings(),
        )

    def get_alert_settings(self) -> AlertSettingsDTO:
        return AlertSettingsDTO(
            enabled=self._settings.BARK_ENABLED
            if hasattr(self._settings, "BARK_ENABLED")
            else False,
            server_url=getattr(self._settings, "BARK_SERVER_URL", None),
            device_key_configured=_mask_bool(getattr(self._settings, "BARK_DEVICE_KEY", None)),
            default_group=getattr(self._settings, "BARK_DEFAULT_GROUP", None),
            alert_levels=["error", "warning", "critical"],
        )

    def get_all_settings(self) -> AllSettingsDTO:
        return AllSettingsDTO(
            llm=self.get_llm_settings(),
            infra=self.get_infra_settings(),
            alert=self.get_alert_settings(),
        )

    def _build_pg_settings(self) -> InfraComponentSettingsDTO:
        db_url = self._settings.DATABASE_URL or ""
        host = ""
        port = 5432
        database = ""
        username = ""
        # Best-effort parse of postgresql://user:pass@host:port/db
        if "://" in db_url:
            rest = db_url.split("://", 1)[1]
            if "@" in rest:
                auth_part, host_part = rest.split("@", 1)
                if ":" in auth_part:
                    username = auth_part.split(":", 1)[0]
                if "/" in host_part:
                    host_port, database = host_part.split("/", 1)
                    if ":" in host_port:
                        parts = host_port.rsplit(":", 1)
                        host = parts[0]
                        try:
                            port = int(parts[1])
                        except ValueError:
                            pass
                    else:
                        host = host_port
            else:
                host_part = rest
                if "/" in host_part:
                    host, database = host_part.split("/", 1)
                else:
                    host = host_part
        return InfraComponentSettingsDTO(
            host=host or "localhost",
            port=port,
            database=database or "marketmind",
            username=username or "postgres",
            password_configured=True,  # DB URL includes password
        )

    def _build_redis_settings(self) -> InfraComponentSettingsDTO:
        redis_url = getattr(self._settings, "REDIS_URL", "")
        host = "localhost"
        port = 6379
        if "://" in redis_url:
            rest = redis_url.split("://", 1)[1]
            if "@" in rest:
                rest = rest.split("@", 1)[1]
            if ":" in rest:
                parts = rest.rsplit(":", 1)
                host = parts[0]
                try:
                    port = int(parts[1].split("/")[0])
                except ValueError:
                    pass
        password_configured = bool(
            getattr(self._settings, "REDIS_PASSWORD", None)
            or (
                "@" in redis_url
                and "://" in redis_url
                and redis_url.split("://", 1)[1].split("@", 1)[0].count(":")
            )
        )
        return InfraComponentSettingsDTO(
            host=host,
            port=port,
            username=None,
            password_configured=password_configured,
        )

    def _build_minio_settings(self) -> MinioSettingsDTO:
        return MinioSettingsDTO(
            endpoint=self._settings.OBJECT_STORAGE_ENDPOINT or "",
            bucket=self._settings.OBJECT_STORAGE_BUCKET or "",
            access_key_configured=_mask_bool(self._settings.OBJECT_STORAGE_ACCESS_KEY),
            secret_key_configured=_mask_bool(self._settings.OBJECT_STORAGE_SECRET_KEY),
            secure=self._settings.OBJECT_STORAGE_SECURE,
        )
