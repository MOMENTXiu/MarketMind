"""MinIO-backed adapter for RegularizedDatasetProvider.

Uses UUID-backed object keys and preserves original filenames in metadata.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.errors import ValidationError
from backend.providers.dtos import (
    RegularizationSidecarReferenceDTO,
    RegularizedDatasetReferenceDTO,
)
from backend.providers.object_storage_provider import ObjectStorageProvider


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_id(value: str) -> str:
    if not value or ".." in value or "/" in value or "\\" in value:
        raise ValidationError(f"Unsafe identifier: {value}")
    return value


def _upload_key(project_id: str, job_id: str, upload_uuid: str, filename: str) -> str:
    return (
        f"projects/{project_id}/analysis/regularization/{job_id}/uploads/{upload_uuid}/{filename}"
    )


def _dataset_key(project_id: str, job_id: str, dataset_uuid: str) -> str:
    return f"projects/{project_id}/analysis/regularization/{job_id}/normalized/{dataset_uuid}.csv"


def _sidecar_key(project_id: str, job_id: str, sidecar_type: str) -> str:
    return f"projects/{project_id}/analysis/regularization/{job_id}/sidecars/{sidecar_type}.json"


class MinioRegularizedDatasetAdapter:
    """Stores raw uploads, normalized datasets, and sidecars in MinIO."""

    def __init__(self, storage: ObjectStorageProvider) -> None:
        self.storage = storage

    def save_raw_upload(
        self,
        project_id: str,
        job_id: str,
        filename: str,
        content: bytes,
    ) -> RegularizedDatasetReferenceDTO:
        upload_uuid = str(uuid.uuid4())
        key = _upload_key(project_id, job_id, upload_uuid, filename)
        stored = self.storage.put(
            key,
            content,
            content_type="application/octet-stream",
            metadata={
                "original_filename": filename,
                "stored_filename": f"{upload_uuid}{Path(filename).suffix or ''}",
            },
        )
        ref_id = "raw-upload"
        return RegularizedDatasetReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            type="raw_upload",
            name=filename,
            storage_key=stored.storage_key,
            url=f"/api/analysis/jobs/{job_id}/datasets/{ref_id}?project_id={project_id}",
            metadata={
                "filename": filename,
                "size_bytes": len(content),
                "upload_uuid": upload_uuid,
            },
            created_at=_now(),
        )

    def load_raw_upload(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizedDatasetReferenceDTO,
    ) -> bytes:
        return self.storage.get(ref.storage_key)

    def save_normalized_dataset(
        self,
        project_id: str,
        job_id: str,
        dataframe: Any,
    ) -> RegularizedDatasetReferenceDTO:
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        dataset_uuid = str(uuid.uuid4())
        key = _dataset_key(project_id, job_id, dataset_uuid)
        csv_bytes = dataframe.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        stored = self.storage.put(
            key,
            csv_bytes,
            content_type="text/csv",
            metadata={
                "rows": str(len(dataframe)),
                "columns": ",".join(map(str, dataframe.columns)),
            },
        )
        ref_id = "normalized-dataset"
        return RegularizedDatasetReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            type="normalized_dataset",
            name="dataset.csv",
            storage_key=stored.storage_key,
            url=f"/api/analysis/jobs/{job_id}/datasets/{ref_id}?project_id={project_id}",
            metadata={"rows": len(dataframe), "columns": list(dataframe.columns)},
            created_at=_now(),
        )

    def load_normalized_dataset(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizedDatasetReferenceDTO,
    ) -> Any:
        data = self.storage.get(ref.storage_key)
        from io import BytesIO

        return pd.read_csv(
            BytesIO(data),
            encoding="utf-8-sig",
            parse_dates=["sale_date"]
            if "sale_date" in pd.read_csv(BytesIO(data), nrows=0, encoding="utf-8-sig").columns
            else [],
            dtype={"user_id": str, "item_id": str, "order_id": str},
        )

    def save_sidecar(
        self,
        project_id: str,
        job_id: str,
        sidecar_type: str,
        payload: dict[str, Any],
    ) -> RegularizationSidecarReferenceDTO:
        _safe_id(sidecar_type)
        key = _sidecar_key(project_id, job_id, sidecar_type)
        data = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        stored = self.storage.put(
            key,
            data,
            content_type="application/json",
            metadata={"sidecar_type": sidecar_type},
        )
        ref_id = f"sidecar:{sidecar_type}"
        return RegularizationSidecarReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            sidecar_type=sidecar_type,
            name=f"{sidecar_type}.json",
            storage_key=stored.storage_key,
            url=f"/api/analysis/jobs/{job_id}/sidecars/{ref_id}?project_id={project_id}",
            metadata={"sidecar_type": sidecar_type},
            created_at=_now(),
        )

    def load_sidecar(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizationSidecarReferenceDTO,
    ) -> dict[str, Any]:
        data = self.storage.get(ref.storage_key)
        return json.loads(data.decode("utf-8"))

    def resolve_dataset_ref(
        self,
        project_id: str,
        job_id: str,
        ref_id: str,
    ) -> RegularizedDatasetReferenceDTO | None:
        prefix = f"projects/{project_id}/analysis/regularization/{job_id}/"
        if ref_id == "raw-upload":
            keys = self.storage.list_keys(f"{prefix}uploads/")
            if not keys:
                return None
            key = keys[0]
            stat = self.storage.stat(key)
            if stat is None:
                return None
            name = stat.metadata.get("original_filename", Path(key).name)
            return RegularizedDatasetReferenceDTO(
                id=ref_id,
                project_id=project_id,
                job_id=job_id,
                type="raw_upload",
                name=name,
                storage_key=key,
                url=f"/api/analysis/jobs/{job_id}/datasets/{ref_id}?project_id={project_id}",
                metadata=stat.metadata,
                created_at=_now(),
            )
        if ref_id == "normalized-dataset":
            keys = self.storage.list_keys(f"{prefix}normalized/")
            if not keys:
                return None
            key = keys[0]
            stat = self.storage.stat(key)
            if stat is None:
                return None
            return RegularizedDatasetReferenceDTO(
                id=ref_id,
                project_id=project_id,
                job_id=job_id,
                type="normalized_dataset",
                name="dataset.csv",
                storage_key=key,
                url=f"/api/analysis/jobs/{job_id}/datasets/{ref_id}?project_id={project_id}",
                metadata=stat.metadata,
                created_at=_now(),
            )
        return None

    def resolve_sidecar_ref(
        self,
        project_id: str,
        job_id: str,
        ref_id: str,
    ) -> RegularizationSidecarReferenceDTO | None:
        prefix = "sidecar:"
        if not ref_id.startswith(prefix):
            return None
        sidecar_type = ref_id[len(prefix) :]
        if not sidecar_type or ".." in sidecar_type or "/" in sidecar_type or "\\" in sidecar_type:
            return None
        key = _sidecar_key(project_id, job_id, sidecar_type)
        stat = self.storage.stat(key)
        if stat is None:
            return None
        return RegularizationSidecarReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            sidecar_type=sidecar_type,
            name=f"{sidecar_type}.json",
            storage_key=key,
            url=f"/api/analysis/jobs/{job_id}/sidecars/{ref_id}?project_id={project_id}",
            metadata={"sidecar_type": sidecar_type},
            created_at=_now(),
        )

    def list_sidecars(
        self,
        project_id: str,
        job_id: str,
    ) -> list[RegularizationSidecarReferenceDTO]:
        prefix = f"projects/{project_id}/analysis/regularization/{job_id}/sidecars/"
        keys = self.storage.list_keys(prefix)
        refs: list[RegularizationSidecarReferenceDTO] = []
        for key in sorted(keys):
            sidecar_type = Path(key).stem
            ref_id = f"sidecar:{sidecar_type}"
            refs.append(
                RegularizationSidecarReferenceDTO(
                    id=ref_id,
                    project_id=project_id,
                    job_id=job_id,
                    sidecar_type=sidecar_type,
                    name=Path(key).name,
                    storage_key=key,
                    url=f"/api/analysis/jobs/{job_id}/sidecars/{ref_id}?project_id={project_id}",
                    metadata={"sidecar_type": sidecar_type},
                    created_at=_now(),
                )
            )
        return refs
