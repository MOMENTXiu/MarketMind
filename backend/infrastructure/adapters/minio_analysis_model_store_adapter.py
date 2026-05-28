"""MinIO-backed adapter for AnalysisModelStoreProvider."""

from __future__ import annotations

import pickle
import re
from collections.abc import Mapping
from typing import Any

from backend.core.errors import InfrastructureError, NotFoundError, ValidationError
from backend.providers.dtos import AnalysisModelReferenceDTO
from backend.providers.object_storage_provider import ObjectStorageProvider


class MinioAnalysisModelStoreAdapter:
    """Persist typed model artifacts in MinIO without exposing local paths."""

    _SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(self, storage: ObjectStorageProvider) -> None:
        self.storage = storage

    def save_model(
        self,
        project_id: str,
        model_type: str,
        payload: Any,
        version: str = "current",
        metadata: Mapping[str, Any] | None = None,
    ) -> AnalysisModelReferenceDTO:
        key = self._model_key(project_id, model_type, version)
        data = pickle.dumps(payload)
        stored = self.storage.put(
            key,
            data,
            content_type="application/octet-stream",
            metadata={k: str(v) for k, v in (metadata or {}).items()},
        )
        return self._ref(project_id, model_type, version, dict(metadata or {}), stored.storage_key)

    def load_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> Any | None:
        key = self._model_key(project_id, model_type, version)
        try:
            data = self.storage.get(key)
            return pickle.loads(data)
        except NotFoundError:
            return None
        except Exception as exc:
            if isinstance(exc, ValidationError):
                raise
            raise InfrastructureError(
                f"Failed to load analysis model {model_type}:{version}"
            ) from exc

    def resolve_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> AnalysisModelReferenceDTO | None:
        key = self._model_key(project_id, model_type, version)
        stat = self.storage.stat(key)
        if stat is None:
            return None
        return self._ref(project_id, model_type, version, {}, key)

    def list_models(self, project_id: str) -> list[AnalysisModelReferenceDTO]:
        self._validate_identifier(project_id, "project_id")
        prefix = f"projects/{project_id}/analysis/models/"
        keys = self.storage.list_keys(prefix)
        refs: list[AnalysisModelReferenceDTO] = []
        for key in sorted(keys):
            parts = key.split("/")
            if len(parts) < 2 or not key.endswith(".pkl"):
                continue
            model_type = parts[-2]
            version = parts[-1][:-4]
            refs.append(self._ref(project_id, model_type, version, {}, key))
        return refs

    def delete_model(self, project_id: str, model_type: str, version: str = "current") -> bool:
        key = self._model_key(project_id, model_type, version)
        return self.storage.delete(key)

    def _model_key(self, project_id: str, model_type: str, version: str) -> str:
        self._validate_identifier(project_id, "project_id")
        self._validate_identifier(model_type, "model_type")
        self._validate_identifier(version, "version")
        return f"projects/{project_id}/analysis/models/{model_type}/{version}.pkl"

    def _ref(
        self,
        project_id: str,
        model_type: str,
        version: str,
        metadata: dict[str, Any],
        storage_key: str,
    ) -> AnalysisModelReferenceDTO:
        model_id = f"{model_type}:{version}"
        return AnalysisModelReferenceDTO(
            id=model_id,
            project_id=project_id,
            type="model",
            name=model_type,
            model_type=model_type,
            version=version,
            url=f"/api/analysis/projects/{project_id}/models/{model_type}/{version}",
            storage_key=storage_key,
            metadata=metadata,
        )

    @classmethod
    def _validate_identifier(cls, value: str, label: str) -> None:
        if not value or not cls._SAFE_IDENTIFIER.fullmatch(value) or ".." in value:
            raise ValidationError(f"Invalid {label}: {value}")
