"""Global association rule analysis pipeline."""

from __future__ import annotations

from backend.abilities.association.analyze_association_rules import analyze_association_rules
from backend.models.schemas import AssociationRuleRequest, AssociationRuleResponse
from backend.providers.container import ProvidersContainer


class AssociationAnalysisPipeline:
    """Run Apriori association analysis on the default dataset."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def analyze(self, request: AssociationRuleRequest) -> AssociationRuleResponse:
        dataset = self.providers.dataset.load_default()
        return analyze_association_rules(
            dataset,
            min_support=request.min_support,
            min_confidence=request.min_confidence,
            min_lift=request.min_lift,
            top_n=request.top_n,
        )
