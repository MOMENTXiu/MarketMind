"""Alert provider interface for external notification services.

Bark HTTP calls are external capabilities that must stay in the
Infrastructure layer. Business layers call this provider only.
"""

from __future__ import annotations

from typing import Protocol

from backend.providers.admin_dtos import TestResultDTO


class AlertProvider(Protocol):
    """Send notifications via external alert channels (Bark, etc.)."""

    def send_test_alert(self, message: str | None = None) -> TestResultDTO:
        """Send a test alert to verify the notification channel works.

        Must NOT be called automatically during health checks — only on
        explicit admin test action.
        """
