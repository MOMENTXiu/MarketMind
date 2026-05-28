"""MinIO-backed adapter for AnalysisArtifactProvider."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.errors import InfrastructureError, ValidationError
from backend.providers.dtos import AnalysisArtifactPayloadDTO, AnalysisArtifactReferenceDTO
from backend.providers.object_storage_provider import ObjectStorageProvider


class MinioAnalysisArtifactAdapter:
    """Persist Analysis V2 artifacts in MinIO."""

    def __init__(self, storage: ObjectStorageProvider) -> None:
        self.storage = storage

    def save_table(self, project_id: str, name: str, rows: Any) -> AnalysisArtifactReferenceDTO:
        safe_name = self._validate_filename(name, ".csv")
        key = self._artifact_key(project_id, "table", safe_name)
        frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        csv_bytes = frame.to_csv(index=False, encoding="utf-8").encode("utf-8")
        stored = self.storage.put(key, csv_bytes, content_type="text/csv")
        return self._ref(
            project_id, "table", safe_name, {"media_type": "text/csv"}, stored.storage_key
        )

    def save_figure(
        self,
        project_id: str,
        name: str,
        content: bytes,
        media_type: str = "image/png",
    ) -> AnalysisArtifactReferenceDTO:
        safe_name = self._validate_filename(name, ".png")
        key = self._artifact_key(project_id, "figure", safe_name)
        stored = self.storage.put(key, content, content_type=media_type)
        return self._ref(
            project_id, "figure", safe_name, {"media_type": media_type}, stored.storage_key
        )

    def save_markdown(
        self,
        project_id: str,
        name: str,
        content: str,
    ) -> AnalysisArtifactReferenceDTO:
        safe_name = self._validate_filename(name, ".md")
        key = self._artifact_key(project_id, "markdown", safe_name)
        stored = self.storage.put(key, content.encode("utf-8"), content_type="text/markdown")
        return self._ref(
            project_id, "markdown", safe_name, {"media_type": "text/markdown"}, stored.storage_key
        )

    def save_json(
        self,
        project_id: str,
        name: str,
        payload: Mapping[str, Any],
    ) -> AnalysisArtifactReferenceDTO:
        safe_name = self._validate_filename(name, ".json")
        key = self._artifact_key(project_id, "json", safe_name)
        data = json.dumps(
            _to_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")
        stored = self.storage.put(key, data, content_type="application/json")
        return self._ref(
            project_id, "json", safe_name, {"media_type": "application/json"}, stored.storage_key
        )

    def resolve_artifact(
        self,
        project_id: str,
        artifact_id: str,
    ) -> AnalysisArtifactReferenceDTO | None:
        self._validate_identifier(project_id, "project_id")
        artifact_type, name = self._parse_artifact_id(artifact_id)
        key = self._artifact_key(project_id, artifact_type, name)
        stat = self.storage.stat(key)
        if stat is None:
            return None
        return self._ref(project_id, artifact_type, name, {"media_type": stat.content_type}, key)

    def load_payload(
        self,
        project_id: str,
        artifact_id: str,
    ) -> AnalysisArtifactPayloadDTO | None:
        self._validate_identifier(project_id, "project_id")
        artifact_type, name = self._parse_artifact_id(artifact_id)
        key = self._artifact_key(project_id, artifact_type, name)
        data = self.storage.get(key)
        ref = self._ref(
            project_id, artifact_type, name, {"media_type": self._media_type(name)}, key
        )
        try:
            if artifact_type == "table":
                from io import StringIO

                rows = pd.read_csv(StringIO(data.decode("utf-8"))).to_dict(orient="records")
                return AnalysisArtifactPayloadDTO(
                    ref=ref,
                    payload_type="table",
                    rows=_to_jsonable(rows),
                )
            if artifact_type == "json":
                return AnalysisArtifactPayloadDTO(
                    ref=ref,
                    payload_type="json",
                    payload=_to_jsonable(json.loads(data.decode("utf-8"))),
                )
            if artifact_type == "markdown":
                return AnalysisArtifactPayloadDTO(
                    ref=ref,
                    payload_type="markdown",
                    content=data.decode("utf-8"),
                )
        except (UnicodeDecodeError, json.JSONDecodeError, pd.errors.ParserError) as error:
            raise InfrastructureError(
                f"Failed to load analysis artifact payload for {project_id}: {artifact_id}"
            ) from error
        raise ValidationError(
            f"Analysis artifact payload is not supported for type: {artifact_type}"
        )

    def _artifact_key(self, project_id: str, artifact_type: str, name: str) -> str:
        self._validate_identifier(project_id, "project_id")
        return f"projects/{project_id}/analysis/artifacts/{artifact_type}/{name}"

    def _ref(
        self,
        project_id: str,
        artifact_type: str,
        name: str,
        metadata: dict[str, Any],
        storage_key: str,
    ) -> AnalysisArtifactReferenceDTO:
        artifact_id = f"{artifact_type}:{name}"
        return AnalysisArtifactReferenceDTO(
            id=artifact_id,
            project_id=project_id,
            type=artifact_type,
            name=name,
            url=f"/api/analysis/projects/{project_id}/artifacts/{artifact_id}",
            storage_key=storage_key,
            metadata=metadata,
        )

    @classmethod
    def _parse_artifact_id(cls, artifact_id: str) -> tuple[str, str]:
        if ":" not in artifact_id:
            raise ValidationError(f"Invalid analysis artifact id: {artifact_id}")
        artifact_type, name = artifact_id.split(":", maxsplit=1)
        if artifact_type not in {"table", "figure", "markdown", "json"}:
            raise ValidationError(f"Invalid analysis artifact type: {artifact_type}")
        return artifact_type, cls._validate_filename(name)

    @staticmethod
    def _media_type(name: str) -> str:
        return {
            ".csv": "text/csv",
            ".json": "application/json",
            ".md": "text/markdown",
            ".png": "image/png",
        }.get(Path(name).suffix, "application/octet-stream")

    @staticmethod
    def _validate_identifier(value: str, label: str) -> None:
        if not value or any(part in {"", ".", ".."} for part in Path(value).parts):
            raise ValidationError(f"Invalid {label}: {value}")
        if Path(value).name != value:
            raise ValidationError(f"Invalid {label}: {value}")

    @staticmethod
    def _validate_filename(name: str, default_suffix: str | None = None) -> str:
        if not name or Path(name).name != name or ".." in Path(name).parts:
            raise ValidationError(f"Invalid analysis artifact name: {name}")
        path = Path(name)
        if default_suffix is not None and path.suffix == "":
            return f"{name}{default_suffix}"
        return name


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(_to_jsonable(key)): _to_jsonable(inner) for key, inner in value.items()}
    if isinstance(value, list | tuple):
        return [_to_jsonable(inner) for inner in value]
    if isinstance(value, str | int | bool) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, pd.DataFrame):
        return _to_jsonable(value.to_dict(orient="records"))
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _to_jsonable(item())
        except (TypeError, ValueError):
            pass
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)
