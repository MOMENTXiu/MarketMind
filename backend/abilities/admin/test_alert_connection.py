"""Test alert (Bark) connection ability."""

from __future__ import annotations

from backend.providers.admin_dtos import TestResultDTO
from backend.providers.alert_provider import AlertProvider


def test_alert_connection(
    alert: AlertProvider,
    message: str | None = None,
) -> TestResultDTO:
    """Send a test alert through the alert provider."""
    return alert.send_test_alert(message=message)
