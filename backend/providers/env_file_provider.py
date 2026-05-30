"""Env file provider interface — read/write .env and LLM config JSON.

Separate from SettingsInspectionProvider (read-only display).
Business layers edit configuration through this provider only.
"""

from __future__ import annotations

from typing import Protocol

from backend.providers.admin_dtos import (
    LlmConfigItemDTO,
    LlmConfigListDTO,
    LlmConfigSaveDTO,
)


class EnvFileProvider(Protocol):
    """Read and write .env file and LLM multi-model configs."""

    # ── .env operations ──────────────────────────────────────────────────

    def read_env(self) -> dict[str, str]:
        """Read all key=value pairs from .env file as a dict."""

    def write_env(self, updates: dict[str, str | None]) -> dict[str, str]:
        """Write key=value pairs to .env. None value deletes the line.
        Returns the full updated dict."""

    def get_env_path(self) -> str:
        """Return the resolved .env file path."""

    # ── LLM config CRUD ──────────────────────────────────────────────────

    def list_llm_configs(self) -> LlmConfigListDTO:
        """Return all saved LLM configs."""

    def get_llm_config(self, config_id: str) -> LlmConfigItemDTO | None:
        """Get a single LLM config by ID."""

    def save_llm_config(
        self, dto: LlmConfigSaveDTO, config_id: str | None = None
    ) -> LlmConfigItemDTO:
        """Create or update an LLM config. config_id=None creates new."""

    def delete_llm_config(self, config_id: str) -> bool:
        """Delete an LLM config. Returns False if not found or is last one."""

    def activate_llm_config(self, config_id: str) -> LlmConfigItemDTO | None:
        """Set a config as active, deactivating all others. Returns updated config or None."""
