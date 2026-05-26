"""Retail V2 dataset preparation orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.abilities.retail.clean_retail_sales import clean_retail_sales
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisArtifactReferenceDTO, RetailDatasetReferenceDTO


@dataclass(frozen=True)
class RetailDatasetPreparationResult:
    project_id: str
    raw_dataset_ref: RetailDatasetReferenceDTO
    clean_sales: Any
    clean_dataset_ref: RetailDatasetReferenceDTO
    quality_summary: dict[str, Any]
    quality_artifact_ref: AnalysisArtifactReferenceDTO


class RetailDatasetPreparationPipeline:
    """Prepare raw Retail V2 sales rows for downstream analysis stages."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(self, project_id: str, filename: str, content: bytes) -> RetailDatasetPreparationResult:
        raw_dataset_ref = self.providers.retail_dataset.save_raw_sales(
            project_id, filename, content
        )
        raw_sales = self.providers.retail_dataset.load_raw_sales(project_id)
        self.providers.retail_dataset.validate_raw_schema(raw_sales)

        clean_result = clean_retail_sales(raw_sales)
        clean_dataset_ref = self.providers.retail_dataset.save_clean_sales(
            project_id,
            clean_result.clean_sales,
        )
        quality_summary = asdict(clean_result.quality_summary)
        quality_artifact_ref = self.providers.analysis_artifacts.save_json(
            project_id,
            "retail_quality_summary.json",
            quality_summary,
        )
        return RetailDatasetPreparationResult(
            project_id=project_id,
            raw_dataset_ref=raw_dataset_ref,
            clean_sales=clean_result.clean_sales,
            clean_dataset_ref=clean_dataset_ref,
            quality_summary=quality_summary,
            quality_artifact_ref=quality_artifact_ref,
        )
