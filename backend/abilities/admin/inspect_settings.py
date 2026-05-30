"""Inspect system settings ability."""

from __future__ import annotations

from backend.providers.admin_dtos import AllSettingsDTO
from backend.providers.settings_inspection_provider import SettingsInspectionProvider


def inspect_all_settings(inspector: SettingsInspectionProvider) -> AllSettingsDTO:
    """Return all settings groups via the inspection provider."""
    return inspector.get_all_settings()
