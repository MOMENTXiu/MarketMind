"""Analysis model store provider interface."""

from collections.abc import Mapping
from typing import Any, Protocol

from backend.providers.dtos import AnalysisModelReferenceDTO


class AnalysisModelStoreProvider(Protocol):
    def save_model(
        self,
        project_id: str,
        model_type: str,
        payload: Any,
        version: str = "current",
        metadata: Mapping[str, Any] | None = None,
    ) -> AnalysisModelReferenceDTO:
        """Persist a typed model artifact behind an opaque model ref."""

    def load_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> Any | None:
        """Load a typed model artifact payload when it exists."""

    def resolve_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> AnalysisModelReferenceDTO | None:
        """Resolve model metadata without exposing local filesystem paths."""

    def list_models(self, project_id: str) -> list[AnalysisModelReferenceDTO]:
        """List model refs for a project."""

    def delete_model(self, project_id: str, model_type: str, version: str = "current") -> bool:
        """Delete one typed model artifact if it exists."""
