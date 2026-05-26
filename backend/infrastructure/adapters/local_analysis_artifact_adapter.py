"""Local project-scoped Analysis V2 artifact adapter."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.errors import InfrastructureError, ValidationError
from backend.providers.dtos import AnalysisArtifactReferenceDTO


class LocalAnalysisArtifactAdapter:
    """Persist Analysis V2 artifacts under project-scoped runtime storage."""

    def __init__(self, data_dir: str = "data") -> None:
        self.projects_dir = Path(data_dir) / "projects"

    def save_table(self, project_id: str, name: str, rows: Any) -> AnalysisArtifactReferenceDTO:
        safe_name = self._validate_filename(name, ".csv")
        path = self._artifact_dir(project_id, "table") / safe_name
        frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False, encoding="utf-8")
        except (OSError, ValueError) as error:
            raise InfrastructureError(f"Failed to save table artifact for {project_id}") from error
        return self._ref(project_id, "table", safe_name, {"media_type": "text/csv"})

    def save_figure(
        self,
        project_id: str,
        name: str,
        content: bytes,
        media_type: str = "image/png",
    ) -> AnalysisArtifactReferenceDTO:
        safe_name = self._validate_filename(name, ".png")
        path = self._artifact_dir(project_id, "figure") / safe_name
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        except OSError as error:
            raise InfrastructureError(f"Failed to save figure artifact for {project_id}") from error
        return self._ref(project_id, "figure", safe_name, {"media_type": media_type})

    def save_markdown(
        self,
        project_id: str,
        name: str,
        content: str,
    ) -> AnalysisArtifactReferenceDTO:
        safe_name = self._validate_filename(name, ".md")
        path = self._artifact_dir(project_id, "markdown") / safe_name
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as error:
            raise InfrastructureError(
                f"Failed to save markdown artifact for {project_id}"
            ) from error
        return self._ref(project_id, "markdown", safe_name, {"media_type": "text/markdown"})

    def save_json(
        self,
        project_id: str,
        name: str,
        payload: Mapping[str, Any],
    ) -> AnalysisArtifactReferenceDTO:
        safe_name = self._validate_filename(name, ".json")
        path = self._artifact_dir(project_id, "json") / safe_name
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as error:
            raise InfrastructureError(f"Failed to save JSON artifact for {project_id}") from error
        return self._ref(project_id, "json", safe_name, {"media_type": "application/json"})

    def resolve_artifact(
        self,
        project_id: str,
        artifact_id: str,
    ) -> AnalysisArtifactReferenceDTO | None:
        self._validate_identifier(project_id, "project_id")
        artifact_type, name = self._parse_artifact_id(artifact_id)
        path = self._artifact_dir(project_id, artifact_type) / name
        if not path.exists():
            return None
        return self._ref(project_id, artifact_type, name, {"media_type": self._media_type(path)})

    def _artifact_dir(self, project_id: str, artifact_type: str) -> Path:
        self._validate_identifier(project_id, "project_id")
        return self.projects_dir / project_id / "analysis" / "artifacts" / artifact_type

    def _ref(
        self,
        project_id: str,
        artifact_type: str,
        name: str,
        metadata: dict[str, Any],
    ) -> AnalysisArtifactReferenceDTO:
        artifact_id = f"{artifact_type}:{name}"
        return AnalysisArtifactReferenceDTO(
            id=artifact_id,
            project_id=project_id,
            type=artifact_type,
            name=name,
            url=f"/api/analysis/projects/{project_id}/artifacts/{artifact_id}",
            storage_key=f"analysis/artifacts/{artifact_type}/{name}",
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
    def _media_type(path: Path) -> str:
        return {
            ".csv": "text/csv",
            ".json": "application/json",
            ".md": "text/markdown",
            ".png": "image/png",
        }.get(path.suffix, "application/octet-stream")

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
