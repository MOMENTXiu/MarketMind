"""Analysis model store provider interface for true model artifacts only."""

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
        """Persist one real model artifact behind an opaque model ref.

        Retail project state, list indexes, and run state are intentionally out of scope.
        """

    def load_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> Any | None:
        """Load one real model artifact payload when it exists."""

    def resolve_model(
        self,
        project_id: str,
        model_type: str,
        version: str = "current",
    ) -> AnalysisModelReferenceDTO | None:
        """Resolve real model metadata without exposing local filesystem paths."""

    def list_models(self, project_id: str) -> list[AnalysisModelReferenceDTO]:
        """List real model refs for one project."""

    def delete_model(self, project_id: str, model_type: str, version: str = "current") -> bool:
        """Delete one real model artifact if it exists."""
