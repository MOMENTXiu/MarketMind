"""Retail Analysis V2 flow orchestration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from backend.business.flows.retail_analysis_state import (
    collect_result_refs,
    empty_marketer_insights,
    format_marketer_insights,
    format_recommendations,
    new_stage,
    project_view,
    public_ref,
    sanitize,
)
from backend.business.pipelines.retail_association_pipeline import RetailAssociationPipeline
from backend.business.pipelines.retail_dataset_preparation_pipeline import (
    RetailDatasetPreparationPipeline,
)
from backend.business.pipelines.retail_feature_engineering_pipeline import (
    RetailFeatureEngineeringPipeline,
)
from backend.business.pipelines.retail_marketer_insight_pipeline import (
    RetailMarketerInsightPipeline,
)
from backend.business.pipelines.retail_recommendation_pipeline import RetailRecommendationPipeline
from backend.business.pipelines.retail_report_pipeline import RetailReportPipeline
from backend.business.pipelines.retail_segmentation_pipeline import RetailSegmentationPipeline
from backend.core.errors import BusinessFlowError, MarketMindError, NotFoundError, ValidationError
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisJobDTO

PROJECT_INDEX_ID = "_retail_analysis_index"
PROJECT_INDEX_MODEL_TYPE = "retail_analysis_project_index"
PROJECT_STATE_MODEL_TYPE = "retail_analysis_project_state"
PROJECT_STATUSES = {"queued", "processing", "completed", "failed"}
STAGE_STATUSES = {"queued", "processing", "completed", "failed", "skipped"}
STAGE_NAMES = (
    "dataset_preparation",
    "feature_engineering",
    "segmentation",
    "association",
    "recommendation",
    "marketer_insights",
    "report",
)


class _StageExecutionError(Exception):
    def __init__(self, stage: str, original: Exception) -> None:
        super().__init__(str(original))
        self.stage = stage
        self.original = original


class RetailAnalysisFlow:
    """Owns the future-facing Retail Analysis V2 project lifecycle."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def create_project(self, name: str, description: str | None = None) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("Retail Analysis project name is required")

        project_id = uuid4().hex
        now = _now()
        state = {
            "id": project_id,
            "name": clean_name,
            "description": (description or "").strip(),
            "status": "queued",
            "stage_statuses": [new_stage(stage_name) for stage_name in STAGE_NAMES],
            "summary": {},
            "dataset_ref": None,
            "quality_summary": {},
            "artifact_refs": [],
            "recommendations": [],
            "marketer_insights": empty_marketer_insights(),
            "job_id": None,
            "trace_id": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        self._save_state(state)
        return project_view(state)

    def list_projects(self) -> dict[str, Any]:
        index = self._load_project_index()
        projects = [dict(project) for project in index.get("projects", [])]
        projects.sort(key=lambda project: str(project.get("created_at") or ""), reverse=True)
        return {"projects": projects, "total": len(projects)}

    def delete_project(self, project_id: str) -> dict[str, Any]:
        self._load_state(project_id)
        model_refs = self.providers.analysis_models.list_models(project_id)
        deleted_models = 0
        for ref in model_refs:
            if self.providers.analysis_models.delete_model(project_id, ref.model_type, ref.version):
                deleted_models += 1
        if not any(ref.model_type == PROJECT_STATE_MODEL_TYPE for ref in model_refs):
            self.providers.analysis_models.delete_model(project_id, PROJECT_STATE_MODEL_TYPE)

        self._remove_project_index_entry(project_id)
        return {"project_id": project_id, "deleted": True, "deleted_models": deleted_models}

    def upload_dataset(self, project_id: str, filename: str, content: bytes) -> dict[str, Any]:
        self._validate_csv_upload(filename, content)
        state = self._load_state(project_id)
        self._prepare_for_dataset_upload(state)
        self._save_state(state)

        try:
            result = RetailDatasetPreparationPipeline(self.providers).run(
                project_id, filename, content
            )
        except MarketMindError as exc:
            self._record_failure(state, "dataset_preparation", exc)
            self._save_state(state)
            raise
        except Exception as exc:
            wrapped = BusinessFlowError(f"Retail dataset preparation failed: {exc}")
            self._record_failure(state, "dataset_preparation", wrapped)
            self._save_state(state)
            raise wrapped from exc

        dataset_ref = public_ref(result.clean_dataset_ref)
        quality_ref = public_ref(result.quality_artifact_ref)
        state["dataset_ref"] = dataset_ref
        state["quality_summary"] = sanitize(result.quality_summary)
        state["summary"] = {
            **dict(state.get("summary", {})),
            "quality_summary": state["quality_summary"],
        }
        self._append_artifact_refs(state, [quality_ref])
        self._set_stage(
            state,
            "dataset_preparation",
            "completed",
            error=None,
            artifact_refs=[quality_ref],
        )
        state["status"] = "queued"
        state["error"] = None
        self._save_state(state)
        return {
            "project_id": project_id,
            "status": state["status"],
            "dataset_ref": dataset_ref,
            "quality_summary": state["quality_summary"],
        }

    def start_analysis(self, project_id: str) -> dict[str, str]:
        state = self._load_state(project_id)
        if state.get("dataset_ref") is None:
            raise ValidationError("Retail Analysis project has no prepared dataset")
        if state.get("status") == "processing":
            return self._processing_run_response(state)

        job_id = uuid4().hex
        trace_id = uuid4().hex
        state["status"] = "processing"
        state["job_id"] = job_id
        state["trace_id"] = trace_id
        state["error"] = None
        self._reset_downstream_outputs(state, preserve_dataset_artifacts=True)
        self._save_state(state)

        self.providers.analysis_jobs.submit_project_analysis(
            AnalysisJobDTO(
                project_id=project_id,
                trigger="retail_analysis_api",
                metadata={"job_id": job_id, "trace_id": trace_id},
            ),
            handler=self.execute_scheduled_analysis,
        )
        return {
            "project_id": project_id,
            "status": "processing",
            "job_id": job_id,
            "trace_id": trace_id,
        }

    def execute_scheduled_analysis(self, project_id: str) -> None:
        try:
            state = self._load_state(project_id)
        except NotFoundError:
            return

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
            self._save_state(state)
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
        self._save_state(state)

    def get_project(self, project_id: str) -> dict[str, Any]:
        return project_view(self._load_state(project_id))

    def list_artifacts(self, project_id: str) -> dict[str, Any]:
        state = self._load_state(project_id)
        return {"project_id": project_id, "artifacts": list(state.get("artifact_refs", []))}

    def get_dataset_ref(self, project_id: str, dataset_id: str) -> dict[str, Any]:
        state = self._load_state(project_id)
        ref = state.get("dataset_ref")
        if not isinstance(ref, dict) or ref.get("id") != dataset_id:
            raise NotFoundError(f"Retail Analysis dataset not found: {dataset_id}")
        return public_ref(ref)

    def get_artifact_ref(self, project_id: str, artifact_id: str) -> dict[str, Any]:
        state = self._load_state(project_id)
        ref = self._find_artifact_ref(state, artifact_id)
        if ref is None or ref.get("type") == "model":
            raise NotFoundError(f"Retail Analysis artifact not found: {artifact_id}")
        return ref

    def get_model_ref(self, project_id: str, model_type: str, version: str) -> dict[str, Any]:
        state = self._load_state(project_id)
        ref = self._find_artifact_ref(state, f"{model_type}:{version}")
        if ref is None or ref.get("type") != "model":
            raise NotFoundError(f"Retail Analysis model not found: {model_type}:{version}")
        return ref

    def list_recommendations(
        self, project_id: str, customer_id: str | None = None, top_k: int = 10
    ) -> dict[str, Any]:
        state = self._load_state(project_id)
        recommendations = list(state.get("recommendations", []))
        if customer_id:
            recommendations = [
                recommendation
                for recommendation in recommendations
                if recommendation.get("customer_id") == customer_id
            ]
        return {
            "project_id": project_id,
            "recommendations": recommendations[:top_k],
        }

    def get_marketer_insights(self, project_id: str) -> dict[str, Any]:
        state = self._load_state(project_id)
        insights = dict(state.get("marketer_insights") or empty_marketer_insights())
        return {"project_id": project_id, **insights}

    def _run_stage(
        self,
        state: dict[str, Any],
        stage: str,
        runner: Callable[[], Any],
    ) -> Any:
        self._set_stage(state, stage, "processing")
        self._save_state(state)
        try:
            result = runner()
        except MarketMindError as exc:
            self._set_stage(state, stage, "failed", error=str(exc))
            self._save_state(state)
            raise _StageExecutionError(stage, exc) from exc
        except Exception as exc:
            wrapped = BusinessFlowError(f"Retail Analysis stage {stage} failed: {exc}")
            self._set_stage(state, stage, "failed", error=str(wrapped))
            self._save_state(state)
            raise _StageExecutionError(stage, wrapped) from exc

        refs = collect_result_refs(result)
        self._append_artifact_refs(state, refs)
        self._set_stage(state, stage, "completed", error=None, artifact_refs=refs)
        self._save_state(state)
        return result

    def _load_state(self, project_id: str) -> dict[str, Any]:
        payload = self.providers.analysis_models.load_model(project_id, PROJECT_STATE_MODEL_TYPE)
        if payload is None:
            raise NotFoundError(f"Retail Analysis project not found: {project_id}")
        if not isinstance(payload, dict):
            raise BusinessFlowError(f"Retail Analysis project state is invalid: {project_id}")
        return dict(payload)

    def _save_state(self, state: dict[str, Any]) -> None:
        status = str(state.get("status", "queued"))
        if status not in PROJECT_STATUSES:
            raise BusinessFlowError(f"Invalid Retail Analysis project status: {status}")
        state["updated_at"] = _now()
        self.providers.analysis_models.save_model(
            str(state["id"]),
            PROJECT_STATE_MODEL_TYPE,
            state,
            metadata={"status": status},
        )
        self._upsert_project_index_entry(state)

    def _load_project_index(self) -> dict[str, Any]:
        payload = self.providers.analysis_models.load_model(
            PROJECT_INDEX_ID,
            PROJECT_INDEX_MODEL_TYPE,
        )
        if payload is None:
            return {"projects": []}
        if not isinstance(payload, dict) or not isinstance(payload.get("projects"), list):
            raise BusinessFlowError("Retail Analysis project index is invalid")
        return {"projects": [dict(project) for project in payload["projects"]]}

    def _save_project_index(self, projects: list[dict[str, Any]]) -> None:
        self.providers.analysis_models.save_model(
            PROJECT_INDEX_ID,
            PROJECT_INDEX_MODEL_TYPE,
            {"projects": projects},
            metadata={"project_count": len(projects)},
        )

    def _upsert_project_index_entry(self, state: dict[str, Any]) -> None:
        entry = project_view(state)
        index = self._load_project_index()
        projects = [project for project in index["projects"] if project.get("id") != entry["id"]]
        projects.append(entry)
        projects.sort(key=lambda project: str(project.get("created_at") or ""), reverse=True)
        self._save_project_index(projects)

    def _remove_project_index_entry(self, project_id: str) -> None:
        index = self._load_project_index()
        projects = [project for project in index["projects"] if project.get("id") != project_id]
        self._save_project_index(projects)

    def _set_stage(
        self,
        state: dict[str, Any],
        stage_name: str,
        status: str,
        error: str | None = None,
        artifact_refs: list[dict[str, Any]] | None = None,
    ) -> None:
        if status not in STAGE_STATUSES:
            raise BusinessFlowError(f"Invalid Retail Analysis stage status: {status}")
        for stage in state["stage_statuses"]:
            if stage["stage"] != stage_name:
                continue
            stage["status"] = status
            stage["error"] = error
            if artifact_refs is not None:
                stage["artifact_refs"] = artifact_refs
            return
        raise BusinessFlowError(f"Unknown Retail Analysis stage: {stage_name}")

    def _append_artifact_refs(self, state: dict[str, Any], refs: list[dict[str, Any]]) -> None:
        artifacts = list(state.get("artifact_refs", []))
        seen = {artifact.get("id") for artifact in artifacts}
        for ref in refs:
            if ref.get("id") in seen:
                continue
            artifacts.append(ref)
            seen.add(ref.get("id"))
        state["artifact_refs"] = artifacts

    def _record_failure(self, state: dict[str, Any], stage_name: str, exc: Exception) -> None:
        message = str(exc) or exc.__class__.__name__
        state["status"] = "failed"
        state["error"] = message
        self._set_stage(state, stage_name, "failed", error=message)
        state["summary"] = {**dict(state.get("summary", {})), "error": message}

    def _record_unhandled_execution_failure(self, state: dict[str, Any], exc: Exception) -> None:
        failed_stage = self._stage_for_unhandled_failure(state)
        wrapped = self._wrap_unhandled_failure(failed_stage, exc)
        self._record_failure(state, failed_stage, wrapped)
        self._skip_stages_after(state, failed_stage)
        self._save_state(state)

    def _prepare_for_dataset_upload(self, state: dict[str, Any]) -> None:
        self._reset_downstream_outputs(state, preserve_dataset_artifacts=False)
        state["dataset_ref"] = None
        state["quality_summary"] = {}
        state["job_id"] = None
        state["trace_id"] = None
        state["error"] = None
        state["status"] = "queued"
        self._set_stage(
            state,
            "dataset_preparation",
            "processing",
            error=None,
            artifact_refs=[],
        )

    def _processing_run_response(self, state: dict[str, Any]) -> dict[str, str]:
        job_id = str(state.get("job_id") or "")
        trace_id = str(state.get("trace_id") or "")
        if not job_id or not trace_id:
            raise BusinessFlowError("Retail Analysis project is processing without job metadata")
        return {
            "project_id": str(state["id"]),
            "status": "processing",
            "job_id": job_id,
            "trace_id": trace_id,
        }

    def _reset_downstream_outputs(
        self,
        state: dict[str, Any],
        preserve_dataset_artifacts: bool,
    ) -> None:
        dataset_artifact_ids = (
            self._dataset_artifact_ids(state) if preserve_dataset_artifacts else set()
        )
        self._reset_downstream_stages(state)
        state["artifact_refs"] = [
            artifact
            for artifact in state.get("artifact_refs", [])
            if isinstance(artifact, dict) and artifact.get("id") in dataset_artifact_ids
        ]
        state["recommendations"] = []
        state["marketer_insights"] = empty_marketer_insights()
        summary = dict(state.get("summary", {}))
        for key in ("completed_stages", "artifact_count", "recommendation_count", "error"):
            summary.pop(key, None)
        if not preserve_dataset_artifacts:
            summary.pop("quality_summary", None)
        state["summary"] = summary

    def _reset_downstream_stages(self, state: dict[str, Any]) -> None:
        for stage in state["stage_statuses"]:
            if stage["stage"] == "dataset_preparation":
                continue
            stage["status"] = "queued"
            stage["error"] = None
            stage["artifact_refs"] = []
        state["recommendations"] = []
        state["marketer_insights"] = empty_marketer_insights()

    def _skip_stages_after(self, state: dict[str, Any], failed_stage: str) -> None:
        failed_index = STAGE_NAMES.index(failed_stage)
        for stage in state["stage_statuses"]:
            if STAGE_NAMES.index(stage["stage"]) <= failed_index:
                continue
            stage["status"] = "skipped"
            stage["error"] = None
            stage["artifact_refs"] = []

    def _dataset_artifact_ids(self, state: dict[str, Any]) -> set[str]:
        for stage in state["stage_statuses"]:
            if stage["stage"] != "dataset_preparation":
                continue
            return {
                str(ref.get("id"))
                for ref in stage.get("artifact_refs", [])
                if isinstance(ref, dict) and ref.get("id")
            }
        return set()

    def _find_artifact_ref(self, state: dict[str, Any], ref_id: str) -> dict[str, Any] | None:
        for ref in state.get("artifact_refs", []):
            if not isinstance(ref, dict) or ref.get("id") != ref_id:
                continue
            return public_ref(ref)
        return None

    def _stage_for_unhandled_failure(self, state: dict[str, Any]) -> str:
        for stage in state["stage_statuses"]:
            if stage["status"] == "processing":
                return str(stage["stage"])

        completed_downstream = [
            stage["stage"]
            for stage in state["stage_statuses"]
            if stage["stage"] != "dataset_preparation" and stage["status"] == "completed"
        ]
        if completed_downstream:
            return str(completed_downstream[-1])
        return "dataset_preparation"

    @staticmethod
    def _wrap_unhandled_failure(stage_name: str, exc: Exception) -> MarketMindError:
        if isinstance(exc, MarketMindError):
            return exc
        return BusinessFlowError(
            f"Retail Analysis scheduled execution failed during {stage_name}: {exc}"
        )

    @staticmethod
    def _validate_csv_upload(filename: str, content: bytes) -> None:
        if not filename.lower().endswith(".csv"):
            raise ValidationError("Retail Analysis dataset upload only supports CSV files")
        if not content:
            raise ValidationError("Retail Analysis dataset upload is empty")


def _now() -> str:
    return datetime.now(UTC).isoformat()
