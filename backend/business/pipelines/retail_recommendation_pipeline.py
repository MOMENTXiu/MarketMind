"""Retail V2 recommendation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.abilities.retail.build_retail_recommendation_signals import (
    RetailRecommendationSignals,
    build_retail_recommendation_signals,
)
from backend.abilities.retail.rank_retail_recommendations import rank_retail_recommendations
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisArtifactReferenceDTO, AnalysisModelReferenceDTO


@dataclass(frozen=True)
class RetailRecommendationResult:
    project_id: str
    signals: RetailRecommendationSignals
    recommendations: Any
    artifact_refs: dict[str, AnalysisArtifactReferenceDTO]
    model_ref: AnalysisModelReferenceDTO


class RetailRecommendationPipeline:
    """Build Retail V2 recommendation signals and ranked recommendation tables."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        clean_sales: Any,
        users: list[str] | None = None,
        top_k: int = 10,
        reliability: dict[str, float] | None = None,
    ) -> RetailRecommendationResult:
        signals = build_retail_recommendation_signals(clean_sales)
        target_users = users if users is not None else sorted(signals.user_items)
        recommendations = rank_retail_recommendations(
            signals,
            target_users,
            top_k=top_k,
            reliability=reliability,
        )
        model_ref = self.providers.analysis_models.save_model(
            project_id,
            "retail_recommendation_signals",
            signals,
            metadata={
                "stage": "recommendation",
                "user_count": len(signals.user_items),
                "item_count": len(signals.popularity),
            },
        )
        artifact_refs = {
            "recommendations": self.providers.analysis_artifacts.save_table(
                project_id, "retail_recommendations.csv", recommendations
            )
        }
        return RetailRecommendationResult(
            project_id=project_id,
            signals=signals,
            recommendations=recommendations,
            artifact_refs=artifact_refs,
            model_ref=model_ref,
        )
