#!/usr/bin/env python3
"""Upload sample CSV files to MinIO on deploy/startup.

Run after infra is up and backend can connect to MinIO:
    uv run python scripts/init-samples-to-minio.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).parent.parent.resolve()
    sys.path.insert(0, str(project_root))

    from backend.core.config import settings
    from backend.infrastructure.factories.provider_factory import _build_minio_storage

    if settings.OBJECT_STORAGE_BACKEND != "minio":
        print(f"OBJECT_STORAGE_BACKEND={settings.OBJECT_STORAGE_BACKEND}, skipping MinIO sample upload.")
        return 0

    storage = _build_minio_storage(settings)

    samples = [
        ("data/samples/marketmind_sample_analysis_data.csv", "samples/marketmind-sample-analysis-data/marketmind_sample_analysis_data.csv", "text/csv"),
    ]

    ok = 0
    for local_path, storage_key, content_type in samples:
        full_path = project_root / local_path
        if not full_path.exists():
            print(f"SKIP: local file not found: {full_path}")
            continue

        data = full_path.read_bytes()
        try:
            storage.put(storage_key, data, content_type=content_type)
            print(f"OK: {local_path} -> {storage_key} ({len(data)} bytes)")
            ok += 1
        except Exception as exc:
            print(f"FAIL: {local_path} -> {storage_key}: {exc}")

    print(f"\nDone: {ok}/{len(samples)} uploaded.")
    return 0 if ok == len(samples) else 1


if __name__ == "__main__":
    raise SystemExit(main())
