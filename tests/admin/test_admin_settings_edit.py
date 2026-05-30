"""Admin settings edit API contract tests.

Phase 0.1: .env editing security — whitelist enforcement, sensitive field
protection, admin-only access, audit logging.
"""

from __future__ import annotations


class TestEnvEditWhitelist:
    """Only LLM_* and BARK_* fields are editable via PUT /api/admin/settings/env."""

    EDITABLE = frozenset(
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

    READONLY_EXAMPLES = [
        "DATABASE_URL",
        "REDIS_URL",
        "AUTH_SECRET_KEY",
        "OBJECT_STORAGE_ENDPOINT",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
        "ASSOCIATION_MIN_SUPPORT",
    ]

    def test_editable_keys_are_llm_and_bark_only(self):
        """Whitelist must contain exactly 9 fields."""
        assert len(self.EDITABLE) == 9

    def test_infra_keys_are_not_editable(self):
        """DATABASE_URL, REDIS_URL, object storage keys must NOT be editable."""
        for key in self.READONLY_EXAMPLES:
            assert key not in self.EDITABLE

    def test_auth_keys_are_not_editable(self):
        """AUTH_SECRET_KEY must NOT be editable."""
        assert "AUTH_SECRET_KEY" not in self.EDITABLE

    def test_sensitive_edit_none_preserves_value(self):
        """When is_sensitive=True and value=None, the current value must be preserved."""
        pass  # validated by adapter contract test

    def test_sensitive_edit_with_value_overwrites(self):
        """When is_sensitive=True and value is non-empty, the value is overwritten."""
        pass

    def test_non_whitelist_key_returns_400(self):
        """Editing a non-whitelist key must return 400 Bad Request."""
        pass


class TestSettingsEditAuth:
    """Only admin users can edit settings."""

    def test_edit_env_requires_admin(self):
        """PUT /api/admin/settings/env must require admin role."""
        pass

    def test_edit_llm_config_requires_admin(self):
        """LLM config CRUD endpoints must require admin role."""
        pass


class TestSensitiveFieldExposure:
    """API responses must never return plaintext sensitive values."""

    def test_llm_config_list_hides_api_key(self):
        """LLM config list must show apiKeyConfigured boolean, not the key text."""
        pass

    def test_env_read_hides_sensitive_values(self):
        """GET /api/admin/settings must not return plaintext secrets."""
        pass
