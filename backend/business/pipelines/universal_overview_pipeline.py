"""Universal overview pipeline."""

from __future__ import annotations

from typing import Any

from backend.abilities.universal_analysis.build_overview import build_overview
from backend.providers.container import ProvidersContainer


class UniversalOverviewPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        job_id: str,
        df: Any,
        cap: dict[str, Any],
    ) -> dict[str, Any]:
        result = build_overview(df, cap)
        json_ref = self.providers.analysis_artifacts.save_json(
            project_id, "universal_overview", result
        )
        return {"result": result, "artifact_ref": json_ref}
