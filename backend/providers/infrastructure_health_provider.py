"""Infrastructure health probe provider interface."""

from __future__ import annotations

from typing import Protocol


class InfrastructureHealthProvider(Protocol):
    """Probe connectivity of runtime infrastructure dependencies."""

    def check_all(self) -> dict[str, dict[str, object]]:
        """Return health status per component.

        Keys: postgres, redis, minio, backend.
        Each value is {"status": "healthy"|"degraded"|"down", "latency_ms": float|None, "detail": str|None}.
        """
