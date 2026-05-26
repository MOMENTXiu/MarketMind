"""Universal summary pipeline."""

from __future__ import annotations

from typing import Any

from backend.abilities.universal_analysis.build_universal_summary import build_universal_summary
from backend.providers.container import ProvidersContainer


class UniversalSummaryPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        job_id: str,
        overview: dict[str, Any],
        profile_segments: dict[str, Any],
        associations: dict[str, Any],
        recommendations: dict[str, Any],
        promotion: dict[str, Any],
    ) -> dict[str, Any]:
        result = build_universal_summary(
            overview, profile_segments, associations, recommendations, promotion
        )
        json_ref = self.providers.analysis_artifacts.save_json(
            project_id, "universal_summary", result
        )
        return {"result": result, "artifact_ref": json_ref}
