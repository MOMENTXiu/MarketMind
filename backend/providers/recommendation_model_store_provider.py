"""Recommendation model artifact provider interface."""

from typing import Any, Protocol

from backend.providers.dtos import ModelArtifactDTO


class RecommendationModelStoreProvider(Protocol):
    def load_model(self) -> ModelArtifactDTO | None:
        """Load the current recommendation model artifact."""

    def save_model(self, payload: Any) -> ModelArtifactDTO:
        """Persist the current recommendation model artifact."""

    def clear_cache(self) -> None:
        """Clear any in-process recommendation model cache."""
