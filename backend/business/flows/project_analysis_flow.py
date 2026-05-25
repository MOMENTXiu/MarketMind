"""Project analysis flow.

Owns the full upload/reanalysis lifecycle of a project. All side effects route
through ``ProvidersContainer``. Preserves the legacy
``analysis_service.run_project_analysis`` contract: ``处理中 -> 已完成 / 失败``
transitions, ``分析失败: ...`` error formatting, report / audio / customers.csv /
recommendation model artifact + cache invalidation. TTS and model-build are
best-effort and never abort the flow.
"""

from __future__ import annotations

import traceback
from typing import Any

from backend.abilities.association.analyze_association_rules import (
    analyze_association_rules,
)
from backend.abilities.clustering.cluster_customers import cluster_customers
from backend.abilities.prediction.forecast_sales import forecast_sales
from backend.abilities.recommendation.build_recommendation_model import (
    build_recommendation_model,
)
from backend.abilities.report.generate_analysis_report import generate_analysis_report
from backend.abilities.report.generate_speech_text import generate_speech_text
from backend.abilities.voice.synthesize_speech import synthesize_speech
from backend.models.project import AnalysisResults, Project, ProjectStatus
from backend.providers.container import ProvidersContainer
from backend.providers.telemetry_dtos import AuditEvent, ErrorEvent, SpanContext


class ProjectAnalysisFlow:
    """Complex lifecycle flow for upload and reanalyze paths."""

    FLOW_NAME = "ProjectAnalysisFlow"

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    async def run(self, project_id: str) -> None:
        project = self.providers.repository.get_project(project_id)
        if project is None:
            return

        span = self._start_span(project_id)
        before = project.status.value
        self._audit(
            "flow.started",
            project_id,
            state_before=before,
            state_after=ProjectStatus.PROCESSING.value,
        )

        try:
            results = await self._execute(project)
        except Exception as exc:
            error_msg = f"分析失败: {exc}\n{traceback.format_exc()}"
            self.providers.repository.mark_analysis_failed(project_id, error_msg)
            self._emit_error(project_id, exc)
            self._audit(
                "flow.stage.failed",
                project_id,
                state_before=before,
                state_after=ProjectStatus.FAILED.value,
                error_type=type(exc).__name__,
            )
            self._end_span(span, "failed")
            return

        self.providers.repository.mark_analysis_completed(project_id, results)
        self._audit(
            "flow.completed",
            project_id,
            state_before=before,
            state_after=ProjectStatus.COMPLETED.value,
        )
        self._end_span(span, "completed")

    async def _execute(self, project: Project) -> AnalysisResults:
        project_id = project.id
        if self.providers.storage.resolve_dataset(project_id) is None:
            raise FileNotFoundError(f"数据集不存在: data/projects/{project_id}/dataset.csv")
        dataset = self.providers.dataset.load_project_dataset(project_id)
        results = AnalysisResults(charts={})

        assoc = analyze_association_rules(
            dataset,
            min_support=project.parameters.min_support,
            min_confidence=project.parameters.min_confidence,
            min_lift=project.parameters.min_lift,
            top_n=10,
        )
        results.association_rules = [
            r.model_dump() if hasattr(r, "model_dump") else r for r in (assoc.rules or [])
        ]
        self._audit("flow.stage.completed", project_id, stage="association_rules")

        forecast = forecast_sales(dataset, project.parameters.forecast_weeks)
        results.prediction_data = forecast.get("data", {})
        self._audit("flow.stage.completed", project_id, stage="forecast_sales")

        cluster = cluster_customers(dataset, project.parameters.n_clusters)
        cluster_data: dict[str, Any] = dict(cluster.get("data", {}) or {})
        rows = cluster_data.get("customer_rows") or []
        customers_asset = self.providers.storage.write_customers(project_id, rows)
        cluster_data["customers_csv"] = str(customers_asset.path)
        results.clustering_data = cluster_data
        self._audit("flow.stage.completed", project_id, stage="cluster_customers")

        report_text = generate_analysis_report(project, results)
        report_asset = self.providers.assets.save_project_report(
            project_id, f"report_{project_id}.md", report_text
        )
        results.report_path = str(report_asset.path)
        self._audit("flow.stage.completed", project_id, stage="report")

        await self._best_effort_audio(project, results)
        self._best_effort_model_build(project, results, dataset)
        return results

    async def _best_effort_audio(self, project: Project, results: AnalysisResults) -> None:
        project_id = project.id
        try:
            text = generate_speech_text(project, results)
            staging = self.providers.storage.get_project_dir(project_id) / (
                f"_tts_staging_{project_id}.mp3"
            )
            synthesis = await synthesize_speech(text, staging, self.providers.speech)
            asset = self.providers.assets.save_project_audio(
                project_id, f"report_{project_id}.mp3", synthesis.audio_path
            )
            results.audio_path = str(asset.path)
            self._audit("flow.stage.completed", project_id, stage="speech")
        except Exception as exc:
            self._audit(
                "flow.stage.failed", project_id, stage="speech", error_type=type(exc).__name__
            )

    def _best_effort_model_build(
        self, project: Project, results: AnalysisResults, dataset: Any
    ) -> None:
        project_id = project.id
        try:
            model = build_recommendation_model(
                dataset, results.association_rules, project.parameters.n_clusters
            )
            if not model.get("success"):
                self._audit(
                    "flow.stage.failed",
                    project_id,
                    stage="model_build",
                    error_type="ModelBuildFailure",
                )
                return
            self.providers.recommendation_models.save_model(model["model_data"])
            self.providers.recommendation_models.clear_cache()
            self._audit("flow.stage.completed", project_id, stage="model_build")
        except Exception as exc:
            self._audit(
                "flow.stage.failed", project_id, stage="model_build", error_type=type(exc).__name__
            )

    # ----- telemetry helpers (best-effort, never raise) -----

    def _start_span(self, project_id: str) -> Any:
        telemetry = self.providers.telemetry
        if telemetry is None:
            return None
        try:
            return telemetry.start_span(
                self.FLOW_NAME,
                SpanContext(trace_id=project_id, span_id=self.FLOW_NAME),
            )
        except Exception:
            return None

    def _end_span(self, span: Any, status: str) -> None:
        telemetry = self.providers.telemetry
        if telemetry is None or span is None:
            return
        try:
            telemetry.end_span(span, status=status)
        except Exception:
            return

    def _audit(self, action: str, project_id: str | None, **fields: Any) -> None:
        telemetry = self.providers.telemetry
        if telemetry is None:
            return
        redaction = {k: v for k, v in fields.items() if v is not None}
        status = "failed" if action.endswith("failed") else "ok"
        try:
            telemetry.emit_audit(
                AuditEvent(
                    actor_id=None,
                    action=action,
                    resource_type="project",
                    resource_id=project_id,
                    status=status,
                    redaction_summary=redaction,
                )
            )
        except Exception:
            return

    def _emit_error(self, project_id: str, exc: Exception) -> None:
        telemetry = self.providers.telemetry
        if telemetry is None:
            return
        try:
            telemetry.emit_error(
                ErrorEvent(
                    error_type=type(exc).__name__,
                    message=str(exc),
                    layer="business",
                    module="flows.project_analysis_flow",
                    operation="run",
                    trace_id=project_id,
                )
            )
        except Exception:
            return
