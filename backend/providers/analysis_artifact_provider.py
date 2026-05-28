"""Analysis artifact provider interface."""

from collections.abc import Mapping
from typing import Any, Protocol

from backend.providers.dtos import AnalysisArtifactPayloadDTO, AnalysisArtifactReferenceDTO


class AnalysisArtifactProvider(Protocol):
    def save_table(self, project_id: str, name: str, rows: Any) -> AnalysisArtifactReferenceDTO:
        """Persist a table artifact and return an opaque API-facing ref."""

    def save_figure(
        self,
        project_id: str,
        name: str,
        content: bytes,
        media_type: str = "image/png",
    ) -> AnalysisArtifactReferenceDTO:
        """Persist a binary figure artifact and return an opaque API-facing ref."""

    def save_markdown(
        self,
        project_id: str,
        name: str,
        content: str,
    ) -> AnalysisArtifactReferenceDTO:
        """Persist a Markdown artifact and return an opaque API-facing ref."""

    def save_json(
        self,
        project_id: str,
        name: str,
        payload: Mapping[str, Any],
    ) -> AnalysisArtifactReferenceDTO:
        """Persist a JSON artifact and return an opaque API-facing ref."""

    def resolve_artifact(
        self,
        project_id: str,
        artifact_id: str,
        owner_user_id: str | None = None,
    ) -> AnalysisArtifactReferenceDTO | None:
        """Resolve artifact metadata without exposing local filesystem paths, optionally scoped to an owner."""

    def load_payload(
        self,
        project_id: str,
        artifact_id: str,
        owner_user_id: str | None = None,
    ) -> AnalysisArtifactPayloadDTO | None:
        """Load a public artifact payload without exposing local filesystem paths, optionally scoped to an owner."""
