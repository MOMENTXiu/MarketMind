"""Local project-scoped Analysis V2 model store adapter."""

import pickle
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from backend.core.errors import InfrastructureError, ValidationError
from backend.providers.dtos import AnalysisModelReferenceDTO


class LocalAnalysisModelStoreAdapter:
    """Persist typed model artifacts without exposing local filesystem paths."""

    _SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(self, data_dir: str = "data") -> None:
        self.projects_dir = Path(data_dir) / "projects"

    def save_model(
        self,
        project_id: str,
        model_type: str,
        payload: Any,
        version: str = "current",
        metadata: Mapping[str, Any] | None = None,
    ) -> AnalysisModelReferenceDTO:
        path = self._model_path(project_id, model_type, version)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as file:
                pickle.dump(payload, file)
        except (OSError, pickle.PickleError, TypeError, ValueError) as error:
            raise InfrastructureError(
                f"Failed to save analysis model {model_type}:{version}"
            ) from error
        return self._ref(project_id, model_type, version, dict(metadata or {}))

    def load_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> Any | None:
        path = self._model_path(project_id, model_type, version)
        if not path.exists():
            return None
        try:
            with path.open("rb") as file:
                return pickle.load(file)
        except (OSError, pickle.PickleError, EOFError, TypeError, ValueError) as error:
            raise InfrastructureError(
                f"Failed to load analysis model {model_type}:{version}"
            ) from error

    def resolve_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> AnalysisModelReferenceDTO | None:
        path = self._model_path(project_id, model_type, version)
        if not path.exists():
            return None
        return self._ref(project_id, model_type, version, {})

    def list_models(self, project_id: str) -> list[AnalysisModelReferenceDTO]:
        self._validate_identifier(project_id, "project_id")
        root = self.projects_dir / project_id / "analysis" / "models"
        if not root.exists():
            return []
        refs: list[AnalysisModelReferenceDTO] = []
        for path in sorted(root.glob("*/*.pkl")):
            model_type = path.parent.name
            version = path.stem
            refs.append(self._ref(project_id, model_type, version, {}))
        return refs

    def delete_model(self, project_id: str, model_type: str, version: str = "current") -> bool:
        path = self._model_path(project_id, model_type, version)
        if not path.exists():
            return False
        try:
            path.unlink()
        except OSError as error:
            raise InfrastructureError(
                f"Failed to delete analysis model {model_type}:{version}"
            ) from error
        return True

    def _model_path(self, project_id: str, model_type: str, version: str) -> Path:
        self._validate_identifier(project_id, "project_id")
        self._validate_identifier(model_type, "model_type")
        self._validate_identifier(version, "version")
        return (
            self.projects_dir / project_id / "analysis" / "models" / model_type / f"{version}.pkl"
        )

    def _ref(
        self,
        project_id: str,
        model_type: str,
        version: str,
        metadata: dict[str, Any],
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
            storage_key=f"analysis/models/{model_type}/{version}.pkl",
            metadata=metadata,
        )

    @classmethod
    def _validate_identifier(cls, value: str, label: str) -> None:
        if not value or not cls._SAFE_IDENTIFIER.fullmatch(value) or ".." in value:
            raise ValidationError(f"Invalid {label}: {value}")
