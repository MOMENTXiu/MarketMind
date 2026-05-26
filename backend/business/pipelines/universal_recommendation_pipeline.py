"""Universal recommendation pipeline."""

from __future__ import annotations

from typing import Any

from backend.abilities.universal_analysis.rank_universal_recommendations import (
    rank_universal_recommendations,
)
from backend.providers.container import ProvidersContainer


class UniversalRecommendationPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        job_id: str,
        df: Any,
        cap: dict[str, Any],
    ) -> dict[str, Any]:
        result = rank_universal_recommendations(df, cap)
        if result.get("status") == "skipped":
            return result
        json_ref = self.providers.analysis_artifacts.save_json(
            project_id, "universal_recommendation", result
        )
        return {"result": result, "artifact_ref": json_ref}
