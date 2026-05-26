"""Universal association pipeline."""

from __future__ import annotations

from typing import Any

from backend.abilities.universal_analysis.mine_universal_associations import (
    mine_universal_associations,
)
from backend.providers.container import ProvidersContainer


class UniversalAssociationPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        job_id: str,
        df: Any,
        cap: dict[str, Any],
    ) -> dict[str, Any]:
        result = mine_universal_associations(df, cap)
        if result.get("status") == "skipped":
            return result
        json_ref = self.providers.analysis_artifacts.save_json(
            project_id, "universal_association", result
        )
        return {"result": result, "artifact_ref": json_ref}
