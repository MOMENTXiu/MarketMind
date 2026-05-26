"""Retail V2 marketer insight orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.abilities.retail.build_marketer_insights import build_marketer_insights
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisArtifactReferenceDTO


@dataclass(frozen=True)
class RetailMarketerInsightResult:
    project_id: str
    segment_value: Any
    bundle_strategy: Any
    promotion_response: Any
    promotion_effect_detail: Any
    customer_uplift: Any
    segment_uplift: Any
    category_strategy: Any
    weights: dict[str, dict[str, float]]
    artifact_refs: dict[str, AnalysisArtifactReferenceDTO]


class RetailMarketerInsightPipeline:
    """Compose marketer-side Retail V2 insight tables from prior stage results."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        clean_sales: Any,
        customer_profile: Any,
        customer_segments: Any,
        high_utility_itemsets: Any | None = None,
        association_rules: Any | None = None,
        top_bundles: int = 20,
    ) -> RetailMarketerInsightResult:
        insights = build_marketer_insights(
            clean_sales,
            customer_profile,
            customer_segments,
            high_utility_itemsets=high_utility_itemsets,
            association_rules=association_rules,
            top_bundles=top_bundles,
        )
        artifact_refs = {
            "segment_value": self.providers.analysis_artifacts.save_table(
                project_id, "retail_marketer_segment_value.csv", insights.segment_value
            ),
            "bundle_strategy": self.providers.analysis_artifacts.save_table(
                project_id, "retail_marketer_bundle_strategy.csv", insights.bundle_strategy
            ),
            "promotion_response": self.providers.analysis_artifacts.save_table(
                project_id, "retail_marketer_promotion_response.csv", insights.promotion_response
            ),
            "promotion_effect_detail": self.providers.analysis_artifacts.save_table(
                project_id,
                "retail_marketer_promotion_effect_detail.csv",
                insights.promotion_effect_detail,
            ),
            "customer_uplift": self.providers.analysis_artifacts.save_table(
                project_id, "retail_marketer_customer_uplift.csv", insights.customer_uplift
            ),
            "segment_uplift": self.providers.analysis_artifacts.save_table(
                project_id, "retail_marketer_segment_uplift.csv", insights.segment_uplift
            ),
            "category_strategy": self.providers.analysis_artifacts.save_table(
                project_id, "retail_marketer_category_strategy.csv", insights.category_strategy
            ),
            "weights": self.providers.analysis_artifacts.save_json(
                project_id,
                "retail_marketer_weights.json",
                insights.weights,
            ),
        }
        return RetailMarketerInsightResult(
            project_id=project_id,
            segment_value=insights.segment_value,
            bundle_strategy=insights.bundle_strategy,
            promotion_response=insights.promotion_response,
            promotion_effect_detail=insights.promotion_effect_detail,
            customer_uplift=insights.customer_uplift,
            segment_uplift=insights.segment_uplift,
            category_strategy=insights.category_strategy,
            weights=insights.weights,
            artifact_refs=artifact_refs,
        )
