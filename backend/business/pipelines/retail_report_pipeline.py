"""Retail V2 Markdown report orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisArtifactReferenceDTO


@dataclass(frozen=True)
class RetailReportResult:
    project_id: str
    markdown: str
    artifact_ref: AnalysisArtifactReferenceDTO


class RetailReportPipeline:
    """Render a concise Retail V2 report from already-computed pipeline results."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def run(
        self,
        project_id: str,
        dataset_result: Any | None = None,
        feature_result: Any | None = None,
        segmentation_result: Any | None = None,
        association_result: Any | None = None,
        recommendation_result: Any | None = None,
        marketer_result: Any | None = None,
    ) -> RetailReportResult:
        markdown = self._render_markdown(
            project_id,
            dataset_result,
            feature_result,
            segmentation_result,
            association_result,
            recommendation_result,
            marketer_result,
        )
        artifact_ref = self.providers.analysis_artifacts.save_markdown(
            project_id,
            "retail_analysis_report.md",
            markdown,
        )
        return RetailReportResult(
            project_id=project_id, markdown=markdown, artifact_ref=artifact_ref
        )

    def _render_markdown(
        self,
        project_id: str,
        dataset_result: Any | None,
        feature_result: Any | None,
        segmentation_result: Any | None,
        association_result: Any | None,
        recommendation_result: Any | None,
        marketer_result: Any | None,
    ) -> str:
        lines = ["# Retail V2 Analysis Report", "", f"Project: `{project_id}`", ""]
        self._append_dataset(lines, dataset_result)
        self._append_features(lines, feature_result)
        self._append_segmentation(lines, segmentation_result)
        self._append_association(lines, association_result)
        self._append_recommendation(lines, recommendation_result)
        self._append_marketer(lines, marketer_result)
        self._append_refs(
            lines,
            _collect_ref_groups(
                dataset_result,
                feature_result,
                segmentation_result,
                association_result,
                recommendation_result,
                marketer_result,
            ),
        )
        return "\n".join(lines).strip() + "\n"

    def _append_dataset(self, lines: list[str], dataset_result: Any | None) -> None:
        if dataset_result is None:
            return
        lines.extend(
            [
                "## Dataset",
                f"- Clean rows: {_table_count(dataset_result.clean_sales)}",
                f"- Quality artifact: {dataset_result.quality_artifact_ref.id}",
                "",
            ]
        )

    def _append_features(self, lines: list[str], feature_result: Any | None) -> None:
        if feature_result is None:
            return
        lines.extend(
            [
                "## Features",
                f"- Customer profiles: {_table_count(feature_result.customer_profile)}",
                f"- Product profiles: {_table_count(feature_result.product_profile)}",
                f"- Repurchase cycles: {_table_count(feature_result.repurchase_cycle)}",
                "",
            ]
        )

    def _append_segmentation(self, lines: list[str], segmentation_result: Any | None) -> None:
        if segmentation_result is None:
            return
        lines.extend(
            [
                "## Segmentation",
                f"- Segment count: {segmentation_result.best_segment_count}",
                f"- Segmented customers: {_table_count(segmentation_result.customer_segments)}",
                "",
            ]
        )

    def _append_association(self, lines: list[str], association_result: Any | None) -> None:
        if association_result is None:
            return
        lines.extend(
            [
                "## Association",
                f"- Item rules: {_table_count(association_result.item_rules)}",
                f"- Category rules: {_table_count(association_result.category_rules)}",
                f"- High utility itemsets: {_table_count(association_result.high_utility_itemsets)}",
                "",
            ]
        )

    def _append_recommendation(self, lines: list[str], recommendation_result: Any | None) -> None:
        if recommendation_result is None:
            return
        lines.extend(
            [
                "## Recommendations",
                f"- Recommendation rows: {_table_count(recommendation_result.recommendations)}",
                f"- Signal model: {recommendation_result.model_ref.id}",
                "",
            ]
        )

    def _append_marketer(self, lines: list[str], marketer_result: Any | None) -> None:
        if marketer_result is None:
            return
        lines.extend(
            [
                "## Marketer Insights",
                f"- Segment value rows: {_table_count(marketer_result.segment_value)}",
                f"- Bundle strategy rows: {_table_count(marketer_result.bundle_strategy)}",
                f"- Category strategy rows: {_table_count(marketer_result.category_strategy)}",
                "",
            ]
        )

    def _append_refs(self, lines: list[str], refs: Iterable[AnalysisArtifactReferenceDTO]) -> None:
        refs = list(refs)
        if not refs:
            return
        lines.extend(["## Artifacts"])
        for ref in refs:
            lines.append(f"- {ref.name}: {ref.id}")
        lines.append("")


def _table_count(table: Any) -> int | str:
    try:
        return len(table)
    except TypeError:
        return "unknown"


def _collect_ref_groups(*results: Any | None) -> list[AnalysisArtifactReferenceDTO]:
    refs: list[AnalysisArtifactReferenceDTO] = []
    for result in results:
        if result is None:
            continue
        artifact_ref = getattr(result, "artifact_ref", None)
        if artifact_ref is not None:
            refs.append(artifact_ref)
        artifact_refs = getattr(result, "artifact_refs", None)
        if isinstance(artifact_refs, dict):
            refs.extend(artifact_refs.values())
        quality_artifact_ref = getattr(result, "quality_artifact_ref", None)
        if quality_artifact_ref is not None:
            refs.append(quality_artifact_ref)
    return refs
