"""Local filesystem adapter for regularized dataset persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.errors import ValidationError
from backend.providers.dtos import (
    RegularizationSidecarReferenceDTO,
    RegularizedDatasetReferenceDTO,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_id(value: str) -> str:
    """Reject path traversal in identifiers."""
    if not value or ".." in value or "/" in value or "\\" in value:
        raise ValidationError(f"Unsafe identifier: {value}")
    return value


def _dataset_dir(base: str, project_id: str, job_id: str) -> Path:
    return (
        Path(base)
        / "projects"
        / _safe_id(project_id)
        / "analysis"
        / "regularization"
        / _safe_id(job_id)
    )


class LocalRegularizedDatasetAdapter:
    """Stores raw uploads, normalized datasets, and JSON sidecars under
    data/projects/{project_id}/analysis/regularization/{job_id}/...
    """

    def __init__(self, data_dir: str) -> None:
        self.data_dir = Path(data_dir)

    def _ensure_dir(self, project_id: str, job_id: str) -> Path:
        d = _dataset_dir(self.data_dir, project_id, job_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_raw_upload(
        self,
        project_id: str,
        job_id: str,
        filename: str,
        content: bytes,
    ) -> RegularizedDatasetReferenceDTO:
        d = self._ensure_dir(project_id, job_id)
        ref_id = "raw-upload"
        path = d / "raw_upload"
        path.write_bytes(content)
        return RegularizedDatasetReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            type="raw_upload",
            name=filename,
            storage_key=f"projects/{project_id}/analysis/regularization/{job_id}/raw_upload",
            url=f"/api/analysis/jobs/{job_id}/datasets/{ref_id}?project_id={project_id}",
            metadata={"filename": filename, "size_bytes": len(content)},
            created_at=_now(),
        )

    def load_raw_upload(
        self,
        project_id: str,
        job_id: str,
        ref: RegularizedDatasetReferenceDTO,
    ) -> bytes:
        d = _dataset_dir(self.data_dir, project_id, job_id)
        path = d / "raw_upload"
        if not path.exists():
            raise FileNotFoundError(f"Raw upload not found: {path}")
        return path.read_bytes()

    def save_normalized_dataset(
        self,
        project_id: str,
        job_id: str,
        dataframe: Any,
    ) -> RegularizedDatasetReferenceDTO:
        d = self._ensure_dir(project_id, job_id)
        ref_id = "normalized-dataset"
        path = d / "dataset.csv"
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        dataframe.to_csv(path, index=False, encoding="utf-8-sig")
        return RegularizedDatasetReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            type="normalized_dataset",
            name="dataset.csv",
            storage_key=f"projects/{project_id}/analysis/regularization/{job_id}/dataset.csv",
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
        d = _dataset_dir(self.data_dir, project_id, job_id)
        path = d / "dataset.csv"
        if not path.exists():
            raise FileNotFoundError(f"Normalized dataset not found: {path}")
        return pd.read_csv(
            path,
            encoding="utf-8-sig",
            parse_dates=["sale_date"]
            if "sale_date" in pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns
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
        d = self._ensure_dir(project_id, job_id)
        _safe_id(sidecar_type)
        ref_id = f"sidecar:{sidecar_type}"
        path = d / f"{sidecar_type}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        return RegularizationSidecarReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            sidecar_type=sidecar_type,
            name=f"{sidecar_type}.json",
            storage_key=f"projects/{project_id}/analysis/regularization/{job_id}/{sidecar_type}.json",
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
        d = _dataset_dir(self.data_dir, project_id, job_id)
        path = d / f"{ref.sidecar_type}.json"
        if not path.exists():
            raise FileNotFoundError(f"Sidecar not found: {path}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def resolve_dataset_ref(
        self,
        project_id: str,
        job_id: str,
        ref_id: str,
    ) -> RegularizedDatasetReferenceDTO | None:
        d = _dataset_dir(self.data_dir, project_id, job_id)
        mapping = {
            "raw-upload": ("raw_upload", "raw_upload"),
            "normalized-dataset": ("dataset.csv", "normalized_dataset"),
        }
        if ref_id not in mapping:
            return None
        name, ds_type = mapping[ref_id]
        path = d / name
        if not path.exists():
            return None
        return RegularizedDatasetReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            type=ds_type,
            name=name if ds_type == "raw_upload" else "dataset.csv",
            storage_key=f"projects/{project_id}/analysis/regularization/{job_id}/{name}",
            url=f"/api/analysis/jobs/{job_id}/datasets/{ref_id}?project_id={project_id}",
            metadata={},
            created_at=_now(),
        )

    def resolve_sidecar_ref(
        self,
        project_id: str,
        job_id: str,
        ref_id: str,
    ) -> RegularizationSidecarReferenceDTO | None:
        d = _dataset_dir(self.data_dir, project_id, job_id)
        prefix = "sidecar:"
        if not ref_id.startswith(prefix):
            return None
        sidecar_type = ref_id[len(prefix) :]
        if not sidecar_type or ".." in sidecar_type or "/" in sidecar_type or "\\" in sidecar_type:
            return None
        path = d / f"{sidecar_type}.json"
        if not path.exists():
            return None
        return RegularizationSidecarReferenceDTO(
            id=ref_id,
            project_id=project_id,
            job_id=job_id,
            sidecar_type=sidecar_type,
            name=path.name,
            storage_key=f"projects/{project_id}/analysis/regularization/{job_id}/{path.name}",
            url=f"/api/analysis/jobs/{job_id}/sidecars/{ref_id}?project_id={project_id}",
            metadata={"sidecar_type": sidecar_type},
            created_at=_now(),
        )

    def list_sidecars(
        self,
        project_id: str,
        job_id: str,
    ) -> list[RegularizationSidecarReferenceDTO]:
        d = _dataset_dir(self.data_dir, project_id, job_id)
        refs: list[RegularizationSidecarReferenceDTO] = []
        for path in sorted(d.glob("*.json")):
            sidecar_type = path.stem
            ref_id = f"sidecar:{sidecar_type}"
            refs.append(
                RegularizationSidecarReferenceDTO(
                    id=ref_id,
                    project_id=project_id,
                    job_id=job_id,
                    sidecar_type=sidecar_type,
                    name=path.name,
                    storage_key=f"projects/{project_id}/analysis/regularization/{job_id}/{path.name}",
                    url=f"/api/analysis/jobs/{job_id}/sidecars/{ref_id}?project_id={project_id}",
                    metadata={"sidecar_type": sidecar_type},
                    created_at=_now(),
                )
            )
        return refs
