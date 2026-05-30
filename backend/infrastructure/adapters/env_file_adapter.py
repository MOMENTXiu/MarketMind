"""Env file adapter — read/write .env file and LLM multi-model JSON config.

Implements EnvFileProvider. All file I/O stays in Infrastructure layer.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from backend.core.errors import InfrastructureError, NotFoundError, ValidationError
from backend.providers.admin_dtos import (
    LlmConfigItemDTO,
    LlmConfigListDTO,
    LlmConfigSaveDTO,
)

# Keys allowed to be edited via admin API
EDITABLE_ENV_KEYS = frozenset(
    {
        "LLM_PROVIDER",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_TIMEOUT_SECONDS",
        "BARK_ENABLED",
        "BARK_SERVER_URL",
        "BARK_DEVICE_KEY",
        "BARK_DEFAULT_GROUP",
    }
)

# Keys whose values must never be returned in plaintext
SENSITIVE_ENV_KEYS = frozenset(
    {
        "LLM_API_KEY",
        "BARK_DEVICE_KEY",
        "AUTH_SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
    }
)


class EnvFileAdapter:
    """File-based adapter implementing EnvFileProvider.

    - .env: key=value line-based, atomic write via tmp+rename, auto-backup
    - LLM configs: stored in a separate JSON file (data/llm-configs.json)
    """

    def __init__(
        self,
        env_path: str = ".env",
        llm_config_path: str = "data/llm-configs.json",
    ) -> None:
        self._env_path = Path(env_path).resolve()
        self._llm_config_path = Path(llm_config_path).resolve()

    # ── .env operations ──────────────────────────────────────────────────────

    def read_env(self) -> dict[str, str]:
        result: dict[str, str] = {}
        if not self._env_path.exists():
            return result
        try:
            for line in self._env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    result[key] = value
        except OSError as exc:
            raise InfrastructureError(f"Failed to read .env: {exc}") from exc
        return result

    def write_env(self, updates: dict[str, str | None]) -> dict[str, str]:
        # Read current state
        current = self.read_env()

        # Validate whitelist
        for key in updates:
            if key not in EDITABLE_ENV_KEYS:
                raise ValidationError(f"Field '{key}' is not editable via admin API")

        # Apply updates
        for key, value in updates.items():
            if value is None:
                current.pop(key, None)
            else:
                current[key] = value

        # Atomic write: .env.tmp → os.replace
        tmp_path = self._env_path.with_suffix(".env.tmp")
        try:
            lines = [f"{k}={_quote_if_needed(v)}\n" for k, v in sorted(current.items())]
            tmp_path.write_text("".join(lines), encoding="utf-8")
            # Backup existing .env if present
            if self._env_path.exists():
                backup = self._env_path.with_suffix(".env.backup")
                shutil.copy2(self._env_path, backup)
            os.replace(tmp_path, self._env_path)
        except OSError as exc:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise InfrastructureError(f"Failed to write .env: {exc}") from exc

        return current

    def get_env_path(self) -> str:
        return str(self._env_path)

    # ── LLM config CRUD ──────────────────────────────────────────────────────

    def list_llm_configs(self) -> LlmConfigListDTO:
        configs = self._read_llm_configs()
        return LlmConfigListDTO(configs=[self._item_to_dto(c) for c in configs])

    def get_llm_config(self, config_id: str) -> LlmConfigItemDTO | None:
        for c in self._read_llm_configs():
            if c.get("id") == config_id:
                return self._item_to_dto(c)
        return None

    def save_llm_config(
        self,
        dto: LlmConfigSaveDTO,
        config_id: str | None = None,
    ) -> LlmConfigItemDTO:
        configs = self._read_llm_configs()
        now = datetime.now(UTC).isoformat()

        if config_id:
            # Update existing
            for c in configs:
                if c.get("id") == config_id:
                    c["name"] = dto.name
                    c["provider"] = dto.provider
                    c["base_url"] = dto.base_url
                    c["model"] = dto.model
                    c["timeout_seconds"] = dto.timeout_seconds
                    if dto.api_key is not None and dto.api_key.strip():
                        c["api_key"] = dto.api_key
                    if dto.is_active:
                        self._deactivate_all(configs)
                        c["is_active"] = True
                    self._write_llm_configs(configs)
                    return self._item_to_dto(c)
            raise NotFoundError(f"LLM config '{config_id}' not found")
        else:
            # Create new
            if dto.is_active:
                self._deactivate_all(configs)
            new_id = f"llm-{uuid4().hex[:8]}"
            record = {
                "id": new_id,
                "name": dto.name,
                "provider": dto.provider,
                "base_url": dto.base_url,
                "api_key": dto.api_key or "",
                "model": dto.model,
                "timeout_seconds": dto.timeout_seconds,
                "is_active": dto.is_active,
                "created_at": now,
            }
            configs.append(record)
            self._write_llm_configs(configs)
            return self._item_to_dto(record)

    def delete_llm_config(self, config_id: str) -> bool:
        configs = self._read_llm_configs()
        if len(configs) <= 1:
            raise ValidationError("Cannot delete the last LLM config")
        filtered = [c for c in configs if c.get("id") != config_id]
        if len(filtered) == len(configs):
            return False  # not found
        self._write_llm_configs(filtered)
        return True

    def activate_llm_config(self, config_id: str) -> LlmConfigItemDTO | None:
        configs = self._read_llm_configs()
        target = None
        for c in configs:
            if c.get("id") == config_id:
                target = c
                break
        if target is None:
            return None
        self._deactivate_all(configs)
        target["is_active"] = True
        self._write_llm_configs(configs)
        return self._item_to_dto(target)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _read_llm_configs(self) -> list[dict]:
        if not self._llm_config_path.exists():
            return []
        try:
            data = json.loads(self._llm_config_path.read_text(encoding="utf-8"))
            return data.get("configs", [])
        except (json.JSONDecodeError, OSError) as exc:
            raise InfrastructureError(f"Failed to read LLM configs: {exc}") from exc

    def _write_llm_configs(self, configs: list[dict]) -> None:
        self._llm_config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp = self._llm_config_path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps({"configs": configs}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, self._llm_config_path)
        except OSError as exc:
            raise InfrastructureError(f"Failed to write LLM configs: {exc}") from exc

    @staticmethod
    def _deactivate_all(configs: list[dict]) -> None:
        for c in configs:
            c["is_active"] = False

    @staticmethod
    def _item_to_dto(record: dict) -> LlmConfigItemDTO:
        return LlmConfigItemDTO(
            id=record.get("id", ""),
            name=record.get("name", ""),
            provider=record.get("provider", "openai"),
            base_url=record.get("base_url"),
            api_key_configured=bool(record.get("api_key", "").strip()),
            model=record.get("model"),
            timeout_seconds=record.get("timeout_seconds", 30),
            is_active=record.get("is_active", False),
            created_at=record.get("created_at"),
        )


def _quote_if_needed(value: str) -> str:
    """Quote values containing spaces or special chars."""
    if any(c in value for c in (" ", "#", "=")):
        return f'"{value}"'
    return value
