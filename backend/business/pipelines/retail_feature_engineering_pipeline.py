"""Retail V2 feature engineering orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.abilities.retail.build_customer_profile import build_customer_profile
from backend.abilities.retail.build_price_rank import build_price_rank
from backend.abilities.retail.build_product_profile import build_product_profile
from backend.abilities.retail.build_repurchase_cycle import (
    aggregate_customer_repurchase_need,
    build_repurchase_cycle,
)
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisArtifactReferenceDTO


@dataclass(frozen=True)
class RetailFeatureEngineeringResult:
    project_id: str
    clean_sales: Any
    price_rank: Any
    repurchase_cycle: Any
    customer_profile: Any
    product_profile: Any
    weights: dict[str, list[float]]
    artifact_refs: dict[str, AnalysisArtifactReferenceDTO]


class RetailFeatureEngineeringPipeline:
    """Build Retail V2 analysis features from clean sales rows."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self, project_id: str, clean_sales: Any | None = None
    ) -> RetailFeatureEngineeringResult:
        sales = (
            clean_sales
            if clean_sales is not None
            else self.providers.retail_dataset.load_clean_sales(project_id)
        )
        price_rank = build_price_rank(sales)
        repurchase_cycle = build_repurchase_cycle(sales)
        customer_profile, promotion_weights = build_customer_profile(sales, price_rank)
        customer_profile = aggregate_customer_repurchase_need(customer_profile, repurchase_cycle)
        product_profile, product_weights = build_product_profile(sales, price_rank)

        artifact_refs = {
            "price_rank": self.providers.analysis_artifacts.save_table(
                project_id, "retail_price_rank.csv", price_rank
            ),
            "repurchase_cycle": self.providers.analysis_artifacts.save_table(
                project_id, "retail_repurchase_cycle.csv", repurchase_cycle
            ),
            "customer_profile": self.providers.analysis_artifacts.save_table(
                project_id, "retail_customer_profile.csv", customer_profile
            ),
            "product_profile": self.providers.analysis_artifacts.save_table(
                project_id, "retail_product_profile.csv", product_profile
            ),
        }
        weights = {
            "promotion_weights": _numeric_list(promotion_weights),
            "product_weights": _numeric_list(product_weights),
        }
        artifact_refs["weights"] = self.providers.analysis_artifacts.save_json(
            project_id,
            "retail_feature_weights.json",
            weights,
        )
        return RetailFeatureEngineeringResult(
            project_id=project_id,
            clean_sales=sales,
            price_rank=price_rank,
            repurchase_cycle=repurchase_cycle,
            customer_profile=customer_profile,
            product_profile=product_profile,
            weights=weights,
            artifact_refs=artifact_refs,
        )


def _numeric_list(values: Any) -> list[float]:
    if hasattr(values, "tolist"):
        values = values.tolist()
    return [float(value) for value in values]
