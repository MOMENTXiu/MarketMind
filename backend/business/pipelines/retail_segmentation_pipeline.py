"""Retail V2 customer segmentation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.abilities.retail.cluster_retail_customers import cluster_retail_customers
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisArtifactReferenceDTO, AnalysisModelReferenceDTO


@dataclass(frozen=True)
class RetailSegmentationResult:
    project_id: str
    customer_segments: Any
    segment_profile: Any
    model_comparison: Any
    feature_columns: list[str]
    best_segment_count: int
    artifact_refs: dict[str, AnalysisArtifactReferenceDTO]
    model_ref: AnalysisModelReferenceDTO


class RetailSegmentationPipeline:
    """Cluster Retail V2 customer profiles and persist segment outputs."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        customer_profile: Any,
        segment_count: int | None = None,
    ) -> RetailSegmentationResult:
        result = cluster_retail_customers(customer_profile, segment_count=segment_count)
        artifact_refs = {
            "customer_segments": self.providers.analysis_artifacts.save_table(
                project_id, "retail_customer_segments.csv", result.customer_segments
            ),
            "segment_profile": self.providers.analysis_artifacts.save_table(
                project_id, "retail_segment_profile.csv", result.segment_profile
            ),
            "model_comparison": self.providers.analysis_artifacts.save_table(
                project_id, "retail_segmentation_model_comparison.csv", result.model_comparison
            ),
        }
        model_payload = {
            "feature_columns": result.feature_columns,
            "best_segment_count": result.best_segment_count,
        }
        model_ref = self.providers.analysis_models.save_model(
            project_id,
            "retail_customer_segmentation",
            model_payload,
            metadata={"stage": "segmentation"},
        )
        return RetailSegmentationResult(
            project_id=project_id,
            customer_segments=result.customer_segments,
            segment_profile=result.segment_profile,
            model_comparison=result.model_comparison,
            feature_columns=result.feature_columns,
            best_segment_count=result.best_segment_count,
            artifact_refs=artifact_refs,
            model_ref=model_ref,
        )
