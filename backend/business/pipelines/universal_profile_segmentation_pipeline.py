"""Universal profile/segmentation pipeline."""

from __future__ import annotations

from typing import Any

from backend.abilities.universal_analysis.build_profile_segments import build_profile_segments
from backend.providers.container import ProvidersContainer


class UniversalProfileSegmentationPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        job_id: str,
        df: Any,
        cap: dict[str, Any],
    ) -> dict[str, Any]:
        result = build_profile_segments(df, cap)
        if result.get("status") == "skipped":
            return result
        json_ref = self.providers.analysis_artifacts.save_json(
            project_id, "universal_profile_segments", result
        )
        model = result.get("model")
        model_ref = None
        if model:
            model_ref = self.providers.analysis_models.save_model(
                project_id, "segmentation", model, metadata={"k": result.get("n_segments")}
            )
        return {"result": result, "artifact_ref": json_ref, "model_ref": model_ref}
