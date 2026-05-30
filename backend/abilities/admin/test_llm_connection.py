"""Test LLM connection ability."""

from __future__ import annotations

import asyncio
import time

from backend.providers.admin_dtos import TestResultDTO
from backend.providers.dtos import LLMRequestDTO
from backend.providers.llm_provider import LLMProvider
from backend.providers.settings_inspection_provider import SettingsInspectionProvider


def test_llm_connection(
    inspector: SettingsInspectionProvider,
    llm: LLMProvider,
) -> TestResultDTO:
    """Verify LLM connectivity by sending a minimal prompt.

    Uses the settings inspection provider to check if LLM is configured,
    then sends a test prompt through the LLM provider.
    """
    settings = inspector.get_llm_settings()
    if not settings.enabled and not settings.api_key_configured:
        return TestResultDTO(
            success=False,
            message="LLM provider is not configured",
        )

    start = time.monotonic()
    try:

        async def _test():
            return await llm.generate_text(LLMRequestDTO(prompt="Hello", max_tokens=5))

        asyncio.run(_test())
        latency_ms = (time.monotonic() - start) * 1000
        return TestResultDTO(
            success=True,
            message="LLM connection successful",
            latency_ms=round(latency_ms, 2),
        )
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return TestResultDTO(
            success=False,
            message=f"LLM connection failed: {exc}",
            latency_ms=round(latency_ms, 2),
        )
