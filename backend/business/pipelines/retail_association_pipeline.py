"""Retail V2 association and high-utility itemset orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.abilities.retail.mine_high_utility_itemsets import mine_high_utility_itemsets
from backend.abilities.retail.mine_retail_association_rules import mine_retail_association_rules
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisArtifactReferenceDTO


@dataclass(frozen=True)
class RetailAssociationResult:
    project_id: str
    item_rules: Any
    category_l3_rules: Any
    category_l2_rules: Any
    category_rules: Any
    comparison_summary: Any
    high_utility_itemsets: Any
    artifact_refs: dict[str, AnalysisArtifactReferenceDTO]


class RetailAssociationPipeline:
    """Mine Retail V2 rules and bundle candidates for downstream stages."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(self, project_id: str, clean_sales: Any) -> RetailAssociationResult:
        rules = mine_retail_association_rules(clean_sales)
        positive_sales = clean_sales[clean_sales["is_return"] == 0]
        high_utility_itemsets = mine_high_utility_itemsets(positive_sales)
        artifact_refs = {
            "item_rules": self.providers.analysis_artifacts.save_table(
                project_id, "retail_item_association_rules.csv", rules.item_rules
            ),
            "category_rules": self.providers.analysis_artifacts.save_table(
                project_id, "retail_category_association_rules.csv", rules.category_rules
            ),
            "comparison_summary": self.providers.analysis_artifacts.save_table(
                project_id, "retail_association_comparison_summary.csv", rules.comparison_summary
            ),
            "high_utility_itemsets": self.providers.analysis_artifacts.save_table(
                project_id, "retail_high_utility_itemsets.csv", high_utility_itemsets
            ),
        }
        return RetailAssociationResult(
            project_id=project_id,
            item_rules=rules.item_rules,
            category_l3_rules=rules.category_l3_rules,
            category_l2_rules=rules.category_l2_rules,
            category_rules=rules.category_rules,
            comparison_summary=rules.comparison_summary,
            high_utility_itemsets=high_utility_itemsets,
            artifact_refs=artifact_refs,
        )
