"""Bark push notification adapter.

External HTTP calls to Bark server stay in this Infrastructure adapter.
Business layers call AlertProvider, not this adapter directly.
"""

from __future__ import annotations

import time

import httpx

from backend.providers.admin_dtos import TestResultDTO
from backend.providers.alert_provider import AlertProvider


class BarkAlertAdapter(AlertProvider):
    """Send push notifications via Bark (https://github.com/Finb/Bark)."""

    def __init__(
        self,
        server_url: str,
        device_key: str,
        default_group: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._server_url = server_url.rstrip("/")
        self._device_key = device_key
        self._default_group = default_group
        self._timeout = timeout_seconds

    def send_test_alert(self, message: str | None = None) -> TestResultDTO:
        msg = message or "MarketMind Admin Console — Test alert"
        title = "MarketMind Admin"
        path = f"/{self._device_key}/{title}/{msg}"
        if self._default_group:
            path += f"?group={self._default_group}"
        url = f"{self._server_url}{path}"

        start = time.monotonic()
        try:
            resp = httpx.get(url, timeout=self._timeout)
            latency_ms = (time.monotonic() - start) * 1000
            data = resp.json() if resp.text else {}
            success = resp.status_code == 200 and data.get("code") == 200
            return TestResultDTO(
                success=success,
                message="Bark test alert sent"
                if success
                else f"Bark returned non-200: {resp.status_code}",
                latency_ms=round(latency_ms, 2),
                detail={"status_code": resp.status_code, "bark_code": data.get("code")},
            )
        except httpx.TimeoutException:
            latency_ms = (time.monotonic() - start) * 1000
            return TestResultDTO(
                success=False,
                message="Bark connection timed out",
                latency_ms=round(latency_ms, 2),
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            return TestResultDTO(
                success=False,
                message=f"Bark connection failed: {exc}",
                latency_ms=round(latency_ms, 2),
            )
