"""Composite infrastructure health probe adapter."""

from __future__ import annotations

import time
from typing import Any


class CompositeInfrastructureHealthAdapter:
    """Probes Postgres, Redis, MinIO and reports per-component status."""

    def __init__(
        self,
        engine: Any | None = None,
        redis_client: Any | None = None,
        minio_storage: Any | None = None,
    ) -> None:
        self._engine = engine
        self._redis = redis_client
        self._minio = minio_storage

    def check_all(self) -> dict[str, dict[str, object]]:
        return {
            "backend": self._check_backend(),
            "postgres": self._check_postgres(),
            "redis": self._check_redis(),
            "minio": self._check_minio(),
        }

    def _check_backend(self) -> dict[str, object]:
        return {"status": "healthy", "latency_ms": 0.0, "detail": None}

    def _check_postgres(self) -> dict[str, object]:
        if self._engine is None:
            return {"status": "down", "latency_ms": None, "detail": "engine not configured"}
        started = time.perf_counter()
        try:
            from sqlalchemy import text

            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            latency = round((time.perf_counter() - started) * 1000, 1)
            return {"status": "healthy", "latency_ms": latency, "detail": None}
        except Exception as exc:
            latency = round((time.perf_counter() - started) * 1000, 1)
            return {"status": "down", "latency_ms": latency, "detail": str(exc)}

    def _check_redis(self) -> dict[str, object]:
        if self._redis is None:
            return {"status": "down", "latency_ms": None, "detail": "client not configured"}
        started = time.perf_counter()
        try:
            self._redis.ping()
            latency = round((time.perf_counter() - started) * 1000, 1)
            return {"status": "healthy", "latency_ms": latency, "detail": None}
        except Exception as exc:
            latency = round((time.perf_counter() - started) * 1000, 1)
            return {"status": "down", "latency_ms": latency, "detail": str(exc)}

    def _check_minio(self) -> dict[str, object]:
        if self._minio is None:
            return {"status": "down", "latency_ms": None, "detail": "storage not configured"}
        started = time.perf_counter()
        try:
            self._minio.health_check()
            latency = round((time.perf_counter() - started) * 1000, 1)
            return {"status": "healthy", "latency_ms": latency, "detail": None}
        except Exception as exc:
            latency = round((time.perf_counter() - started) * 1000, 1)
            return {"status": "down", "latency_ms": latency, "detail": str(exc)}
