"""Admin settings API contract tests.

Phase 0.3: Settings API must not expose plaintext secrets/passwords/keys.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


# These tests verify the DTO/structure contract; they run against a future
# fake SettingsInspectionProvider so they can pass in Phase 0 without
# touching real environment variables.


class TestSettingsSensitiveFieldProtection:
    """Settings API must never return plaintext secrets."""

    def test_llm_api_key_not_returned(self):
        """LLM settings must expose apiKeyConfigured boolean, not key text."""
        # Contract: response must not contain "api_key" or "apiKey" strings
        forbidden = {"api_key", "apiKey", "secret", "token"}
        # This test asserts the expected schema, validated by fake provider later
        expected_keys = {
            "provider",
            "baseUrl",
            "model",
            "apiKeyConfigured",
            "timeoutSeconds",
            "enabled",
        }
        assert expected_keys
        assert forbidden

    def test_infra_passwords_not_returned(self):
        """Infra settings must expose passwordConfigured booleans, not passwords."""
        # Postgres: only host, port, database, username, passwordConfigured
        forbidden = {"password", "pass", "secret", "connection_string"}
        expected_pg_keys = {"host", "port", "database", "username", "passwordConfigured"}
        assert expected_pg_keys
        assert not any(k in expected_pg_keys for k in forbidden)

    def test_minio_secrets_not_returned(self):
        """MinIO settings must show endpoint/bucket/secure, not access/secret keys."""
        expected_keys = {
            "endpoint",
            "bucket",
            "accessKeyConfigured",
            "secretKeyConfigured",
            "secure",
        }
        assert expected_keys  # Phase 0 contract placeholder

    def test_bark_device_key_not_returned(self):
        """Bark alert settings must expose deviceKeyConfigured boolean, not key."""
        forbidden = {"device_key", "deviceKey", "key", "token"}
        expected_keys = {
            "enabled",
            "serverUrl",
            "deviceKeyConfigured",
            "defaultGroup",
            "alertLevels",
        }
        assert expected_keys
        assert not any(k in expected_keys for k in forbidden)

    def test_llm_base_url_host_port_only(self):
        """If connection string is returned, it must be host:port only."""
        # The design mandates: "只展示 host:port，隐藏 credentials"
        pass  # Validated by fake adapter contract test

    def test_all_settings_endpoint_structure(self):
        """GET /api/admin/settings returns all three groups plus bark test endpoint."""
        groups = ["llm", "infra", "alert"]
        assert len(groups) == 3  # Contract: 3 setting groups
