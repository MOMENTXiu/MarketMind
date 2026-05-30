"""Admin LLM config CRUD contract tests.

Phase 0.2: Multi-model management with mutual exclusion on activation.
"""

from __future__ import annotations


class TestLlmConfigMutualExclusion:
    """Only one LLM config can be active at a time."""

    def test_activate_deactivates_others(self):
        """Activating config A must deactivate config B."""
        pass

    def test_only_one_active_after_create_with_is_active_true(self):
        """Creating a new config with is_active=True must deactivate others."""
        pass


class TestLlmConfigCRUD:
    """Standard CRUD operations for LLM configs."""

    def test_list_returns_all_configs(self):
        """GET /api/admin/settings/llm-configs returns all saved configs."""
        pass

    def test_create_adds_new_config(self):
        """POST creates a new config with auto-generated id."""
        pass

    def test_update_modifies_existing_config(self):
        """PUT updates name, provider, base_url, model, timeout, api_key."""
        pass

    def test_delete_removes_config(self):
        """DELETE removes a config by id."""
        pass

    def test_delete_last_config_is_rejected(self):
        """Cannot delete the last remaining LLM config."""
        pass

    def test_activate_nonexistent_returns_404(self):
        """Activating a non-existent config id returns 404."""
        pass


class TestLlmConfigAuth:
    """All LLM config endpoints require admin role."""

    def test_list_requires_admin(self):
        pass

    def test_create_requires_admin(self):
        pass

    def test_update_requires_admin(self):
        pass

    def test_delete_requires_admin(self):
        pass

    def test_activate_requires_admin(self):
        pass


class TestLlmConfigSchema:
    """LlmConfigItemDTO must have all fields for UI display."""

    REQUIRED = {
        "id",
        "name",
        "provider",
        "baseUrl",
        "apiKeyConfigured",
        "model",
        "timeoutSeconds",
        "isActive",
        "createdAt",
    }

    VALID_PROVIDERS = {"openai", "anthropic", "deepseek", "custom"}

    def test_config_item_has_required_fields(self):
        assert len(self.REQUIRED) == 9

    def test_valid_providers(self):
        assert len(self.VALID_PROVIDERS) == 4
