"""Manage .env settings ability — whitelist validation and sensitive field handling."""

from __future__ import annotations

from backend.core.errors import ValidationError
from backend.providers.admin_dtos import EnvSettingsUpdateDTO
from backend.providers.env_file_provider import EnvFileProvider

EDITABLE_KEYS = frozenset(
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

SENSITIVE_KEYS = frozenset(
    {
        "LLM_API_KEY",
        "BARK_DEVICE_KEY",
    }
)


def update_env_settings(
    dto: EnvSettingsUpdateDTO,
    env_file: EnvFileProvider,
) -> dict[str, str]:
    """Apply validated .env updates with sensitive-field preservation."""
    # Validate whitelist
    for edit in dto.updates:
        if edit.key not in EDITABLE_KEYS:
            raise ValidationError(f"Field '{edit.key}' is not editable via admin API")

    # Build update dict
    current = env_file.read_env()
    updates: dict[str, str | None] = {}
    for edit in dto.updates:
        if edit.key in SENSITIVE_KEYS:
            if edit.value is None:
                # Preserve existing value
                updates[edit.key] = current.get(edit.key)
            elif edit.value == "":
                updates[edit.key] = None  # clear the key
            else:
                updates[edit.key] = edit.value
        else:
            updates[edit.key] = edit.value if edit.value is not None else ""

    return env_file.write_env(updates)
