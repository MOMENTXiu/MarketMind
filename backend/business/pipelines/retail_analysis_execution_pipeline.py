"""Retail V2 scheduled analysis execution orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.business.flows.retail_analysis_state import (
    collect_result_refs,
    format_marketer_insights,
    format_recommendations,
)
from backend.business.pipelines.retail_association_pipeline import RetailAssociationPipeline
from backend.business.pipelines.retail_feature_engineering_pipeline import (
    RetailFeatureEngineeringPipeline,
)
from backend.business.pipelines.retail_marketer_insight_pipeline import (
    RetailMarketerInsightPipeline,
)
from backend.business.pipelines.retail_recommendation_pipeline import RetailRecommendationPipeline
from backend.business.pipelines.retail_report_pipeline import RetailReportPipeline
from backend.business.pipelines.retail_segmentation_pipeline import RetailSegmentationPipeline
from backend.core.errors import BusinessFlowError, MarketMindError
from backend.providers.container import ProvidersContainer

SaveState = Callable[[dict[str, Any], str | None], None]
SetStage = Callable[
    [dict[str, Any], str, str, str | None, list[dict[str, Any]] | None],
    None,
]
AppendArtifactRefs = Callable[[dict[str, Any], list[dict[str, Any]]], None]
RecordFailure = Callable[[dict[str, Any], str, Exception], None]
RecordUnhandledExecutionFailure = Callable[[dict[str, Any], Exception], None]
SkipStagesAfter = Callable[[dict[str, Any], str], None]


class _StageExecutionError(Exception):
    def __init__(self, stage: str, original: Exception) -> None:
        super().__init__(str(original))
        self.stage = stage
        self.original = original


class RetailAnalysisExecutionPipeline:
    """Run the scheduled Retail V2 analysis stages with persisted state transitions."""

    def __init__(
        self,
        providers: ProvidersContainer,
        *,
        save_state: SaveState,
        set_stage: SetStage,
        append_artifact_refs: AppendArtifactRefs,
        record_failure: RecordFailure,
        record_unhandled_execution_failure: RecordUnhandledExecutionFailure,
        skip_stages_after: SkipStagesAfter,
    ) -> None:
        self.providers = providers
        self._save_state = save_state
        self._set_stage = set_stage
        self._append_artifact_refs = append_artifact_refs
        self._record_failure = record_failure
        self._record_unhandled_execution_failure = record_unhandled_execution_failure
        self._skip_stages_after = skip_stages_after

    def run(self, state: dict[str, Any]) -> None:
        project_id = str(state["id"])
        try:
            clean_sales = self.providers.retail_dataset.load_clean_sales(project_id)
            feature_result = self._run_stage(
                state,
                "feature_engineering",
                lambda: RetailFeatureEngineeringPipeline(self.providers).run(
                    project_id, clean_sales
                ),
            )
            segmentation_result = self._run_stage(
                state,
                "segmentation",
                lambda: RetailSegmentationPipeline(self.providers).run(
                    project_id,
                    feature_result.customer_profile,
                ),
            )
            association_result = self._run_stage(
                state,
                "association",
                lambda: RetailAssociationPipeline(self.providers).run(project_id, clean_sales),
            )
            recommendation_result = self._run_stage(
                state,
                "recommendation",
                lambda: RetailRecommendationPipeline(self.providers).run(project_id, clean_sales),
            )
            marketer_result = self._run_stage(
                state,
                "marketer_insights",
                lambda: RetailMarketerInsightPipeline(self.providers).run(
                    project_id,
                    clean_sales,
                    feature_result.customer_profile,
                    segmentation_result.customer_segments,
                    high_utility_itemsets=association_result.high_utility_itemsets,
                    association_rules=association_result.category_rules,
                ),
            )
            self._run_stage(
                state,
                "report",
                lambda: RetailReportPipeline(self.providers).run(
                    project_id,
                    feature_result=feature_result,
                    segmentation_result=segmentation_result,
                    association_result=association_result,
                    recommendation_result=recommendation_result,
                    marketer_result=marketer_result,
                ),
            )
        except _StageExecutionError as exc:
            self._record_failure(state, exc.stage, exc.original)
            self._skip_stages_after(state, exc.stage)
            self._save_state(state, None)
            return
        except Exception as exc:
            self._record_unhandled_execution_failure(state, exc)
            return

        try:
            recommendations = format_recommendations(recommendation_result.recommendations)
            marketer_insights = format_marketer_insights(marketer_result)
        except Exception as exc:
            self._record_unhandled_execution_failure(state, exc)
            return

        state["status"] = "completed"
        state["error"] = None
        state["recommendations"] = recommendations
        state["marketer_insights"] = marketer_insights
        state["summary"] = {
            **dict(state.get("summary", {})),
            "completed_stages": len(
                [stage for stage in state["stage_statuses"] if stage["status"] == "completed"]
            ),
            "artifact_count": len(state["artifact_refs"]),
            "recommendation_count": len(state["recommendations"]),
        }
        self._save_state(state, None)

    def _run_stage(
        self,
        state: dict[str, Any],
        stage: str,
        runner: Callable[[], Any],
    ) -> Any:
        self._set_stage(state, stage, "processing")
        self._save_state(state, "state_changed")
        try:
            result = runner()
        except MarketMindError as exc:
            self._set_stage(state, stage, "failed", error=str(exc))
            self._save_state(state, None)
            raise _StageExecutionError(stage, exc) from exc
        except Exception as exc:
            wrapped = BusinessFlowError(f"Retail Analysis stage {stage} failed: {exc}")
            self._set_stage(state, stage, "failed", error=str(wrapped))
            self._save_state(state, None)
            raise _StageExecutionError(stage, wrapped) from exc

        refs = collect_result_refs(result)
        self._append_artifact_refs(state, refs)
        self._set_stage(state, stage, "completed", error=None, artifact_refs=refs)
        self._save_state(state, "artifact_ready" if refs else "state_changed")
        return result
