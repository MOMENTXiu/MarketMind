"""Settings inspection provider interface.

Business layers read settings only through this provider; they must not
import backend.core.config or read environment variables directly.
"""

from __future__ import annotations

from typing import Protocol

from backend.providers.admin_dtos import (
    AlertSettingsDTO,
    AllSettingsDTO,
    InfraSettingsDTO,
    LlmSettingsDTO,
)


class SettingsInspectionProvider(Protocol):
    """Read-only inspection of system configuration for the admin console.

    Sensitive fields (API keys, passwords, device keys) are never returned
    as plaintext — only as boolean configured/not-configured indicators.
    """

    def get_llm_settings(self) -> LlmSettingsDTO:
        """Return LLM provider configuration with API key redacted."""

    def get_infra_settings(self) -> InfraSettingsDTO:
        """Return infrastructure configuration with passwords/secrets redacted."""

    def get_alert_settings(self) -> AlertSettingsDTO:
        """Return alert (Bark) configuration with device key redacted."""

    def get_all_settings(self) -> AllSettingsDTO:
        """Return all settings groups in a single call."""
