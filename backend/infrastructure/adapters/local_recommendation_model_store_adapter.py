"""Local recommendation model artifact store adapter."""

import pickle
from collections.abc import Callable
from pathlib import Path
from typing import Any

from backend.providers.dtos import ModelArtifactDTO


class LocalRecommendationModelStoreAdapter:
    """Load and save the current pickle-based recommendation model artifact."""

    def __init__(
        self,
        model_path: str = "backend/data/model_data.pkl",
        cache_clearer: Callable[[], None] | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.cache_clearer = cache_clearer

    def load_model(self) -> ModelArtifactDTO | None:
        if not self.model_path.exists():
            return None
        with open(self.model_path, "rb") as file:
            payload = pickle.load(file)
        return ModelArtifactDTO(path=self.model_path, payload=payload)

    def save_model(self, payload: Any) -> ModelArtifactDTO:
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as file:
            pickle.dump(payload, file)
        return ModelArtifactDTO(path=self.model_path, payload=payload)

    def clear_cache(self) -> None:
        if self.cache_clearer is not None:
            self.cache_clearer()
