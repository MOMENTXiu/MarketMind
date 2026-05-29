"""Data Processing Analysis Flow: orchestrates regularization and universal analysis."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.business.flows.data_processing_analysis_state import (
    STAGE_NAMES,
    append_output_refs,
    build_data_processing_state_event,
    job_view,
    new_job_state,
    set_stage,
)
from backend.business.pipelines.dataset_regularization_pipeline import (
    DatasetRegularizationPipeline,
)
from backend.business.pipelines.universal_association_pipeline import (
    UniversalAssociationPipeline,
)
from backend.business.pipelines.universal_overview_pipeline import UniversalOverviewPipeline
from backend.business.pipelines.universal_profile_segmentation_pipeline import (
    UniversalProfileSegmentationPipeline,
)
from backend.business.pipelines.universal_promotion_pipeline import UniversalPromotionPipeline
from backend.business.pipelines.universal_recommendation_pipeline import (
    UniversalRecommendationPipeline,
)
from backend.business.pipelines.universal_summary_pipeline import UniversalSummaryPipeline
from backend.core.errors import (
    BusinessFlowError,
    MarketMindError,
    NotFoundError,
    ValidationError,
)
from backend.providers.auth_dtos import AuthenticatedUserContext
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisJobDTO

JOB_STATE_MODEL_TYPE = "data_processing_analysis_state"


class _StageExecutionError(Exception):
    def __init__(self, stage: str, original: Exception) -> None:
        super().__init__(str(original))
        self.stage = stage
        self.original = original


class DataProcessingAnalysisFlow:
    """Owns the data-processing chain lifecycle from upload to final result."""

    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def create_job(self, project_id: str, name: str, user_context: AuthenticatedUserContext | None = None) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("Analysis job name is required")
        state = new_job_state(project_id, clean_name)
        self._save_state(state)
        return job_view(state)

    def upload_raw_dataset(
        self, project_id: str, job_id: str, filename: str, content: bytes, user_context: AuthenticatedUserContext | None = None
    ) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        self._validate_upload(filename, content)
        state = self._load_state(job_id)
        if state["project_id"] != project_id:
            raise ValidationError("Job does not belong to project")
        self._reset_job(state)
        self._save_state(state)

        raw_ref = self.providers.regularized_dataset.save_raw_upload(
            project_id, job_id, filename, content
        )
        append_output_refs(state, [self._public_ref(raw_ref)])
        self._save_state(state)
        return job_view(state)

    def regularize(self, project_id: str, job_id: str, user_context: AuthenticatedUserContext | None = None) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        state = self._load_state(job_id)
        if state["project_id"] != project_id:
            raise ValidationError("Job does not belong to project")

        set_stage(state, "dataset_regularization", "processing")
        self._save_state(state)

        try:
            raw_ref = self.providers.regularized_dataset.resolve_dataset_ref(
                project_id, job_id, "raw-upload"
            )
            if raw_ref is None:
                raise ValidationError("No raw dataset uploaded")
            content = self.providers.regularized_dataset.load_raw_upload(
                project_id, job_id, raw_ref
            )
            filename = raw_ref.name

            result = DatasetRegularizationPipeline(self.providers).run(
                project_id, job_id, filename, content
            )
        except MarketMindError as exc:
            set_stage(state, "dataset_regularization", "failed", error=str(exc))
            state["status"] = "failed"
            state["error"] = str(exc)
            self._save_state(state)
            raise
        except Exception as exc:
            wrapped = BusinessFlowError(f"Dataset regularization failed: {exc}")
            set_stage(state, "dataset_regularization", "failed", error=str(wrapped))
            state["status"] = "failed"
            state["error"] = str(wrapped)
            self._save_state(state)
            raise wrapped from exc

        refs = [
            self._public_ref(result.normalized_dataset_ref),
            self._public_ref(result.mapping_ref),
            self._public_ref(result.mapping_detail_ref),
            self._public_ref(result.profile_ref),
            self._public_ref(result.quality_ref),
            self._public_ref(result.capability_ref),
            self._public_ref(result.manifest_ref),
            self._public_ref(result.preview_ref),
        ]
        append_output_refs(state, refs)
        state["quality"] = result.quality
        state["capability"] = result.capability

        if result.needs_review:
            set_stage(state, "dataset_regularization", "needs_review", artifact_refs=refs)
            state["status"] = "needs_review"
        else:
            set_stage(state, "dataset_regularization", "completed", artifact_refs=refs)
            state["status"] = "queued"
        state["error"] = None
        self._save_state(state)
        return job_view(state)

    def run_analysis(self, project_id: str, job_id: str, user_context: AuthenticatedUserContext | None = None) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        state = self._load_state(job_id)
        if state["project_id"] != project_id:
            raise ValidationError("Job does not belong to project")
        if state.get("status") == "processing":
            return job_view(state)

        self._assert_ready_for_analysis(state, project_id, job_id)

        state["status"] = "processing"
        state["error"] = None
        self._reset_analysis_stages(state)
        self._save_state(state)

        self.providers.analysis_jobs.submit_project_analysis(
            AnalysisJobDTO(
                project_id=project_id,
                trigger="data_processing_analysis",
                metadata={"job_id": job_id},
            ),
            handler=lambda pid: self._execute_analysis(job_id),
        )
        return job_view(state)

    def _execute_analysis(self, job_id: str) -> None:
        try:
            state = self._load_state(job_id)
        except NotFoundError:
            return

        project_id = state["project_id"]
        cap = state.get("capability", {})

        try:
            norm_ref = self.providers.regularized_dataset.resolve_dataset_ref(
                project_id, job_id, "normalized-dataset"
            )
            if norm_ref is None:
                raise BusinessFlowError("No normalized dataset found")
            df = self.providers.regularized_dataset.load_normalized_dataset(
                project_id, job_id, norm_ref
            )

            overview_result = self._run_stage(
                state,
                "overview",
                lambda: UniversalOverviewPipeline(self.providers).run(project_id, job_id, df, cap),
            )

            profile_result = self._run_stage(
                state,
                "profile_segmentation",
                lambda: UniversalProfileSegmentationPipeline(self.providers).run(
                    project_id, job_id, df, cap
                ),
            )

            association_result = self._run_stage(
                state,
                "association",
                lambda: UniversalAssociationPipeline(self.providers).run(
                    project_id, job_id, df, cap
                ),
            )

            recommendation_result = self._run_stage(
                state,
                "recommendation",
                lambda: UniversalRecommendationPipeline(self.providers).run(
                    project_id, job_id, df, cap
                ),
            )

            promotion_result = self._run_stage(
                state,
                "promotion",
                lambda: UniversalPromotionPipeline(self.providers).run(project_id, job_id, df, cap),
            )

            self._run_stage(
                state,
                "summary",
                lambda: UniversalSummaryPipeline(self.providers).run(
                    project_id,
                    job_id,
                    overview_result.get("result", {}),
                    profile_result.get("result", {}),
                    association_result.get("result", {}),
                    recommendation_result.get("result", {}),
                    promotion_result.get("result", {}),
                ),
            )

        except _StageExecutionError as exc:
            self._record_failure(state, exc.stage, exc.original)
            self._skip_stages_after(state, exc.stage)
            self._save_state(state)
            return
        except Exception as exc:
            self._record_unhandled_failure(state, exc)
            return

        state["status"] = "completed"
        state["error"] = None
        self._save_state(state)

    def get_dataset_ref(self, project_id: str, job_id: str, dataset_id: str, user_context: AuthenticatedUserContext | None = None) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        state = self._load_state(job_id)
        if state["project_id"] != project_id:
            raise ValidationError("Job does not belong to project")
        ref = self.providers.regularized_dataset.resolve_dataset_ref(project_id, job_id, dataset_id)
        if ref is None:
            raise NotFoundError(f"Dataset ref not found: {dataset_id}")
        return self._public_ref(ref)

    def get_sidecar_ref(self, project_id: str, job_id: str, sidecar_id: str, user_context: AuthenticatedUserContext | None = None) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        state = self._load_state(job_id)
        if state["project_id"] != project_id:
            raise ValidationError("Job does not belong to project")
        ref = self.providers.regularized_dataset.resolve_sidecar_ref(project_id, job_id, sidecar_id)
        if ref is None:
            raise NotFoundError(f"Sidecar ref not found: {sidecar_id}")
        return self._public_ref(ref)

    def load_sidecar(self, project_id: str, job_id: str, sidecar_id: str, user_context: AuthenticatedUserContext | None = None) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        state = self._load_state(job_id)
        if state["project_id"] != project_id:
            raise ValidationError("Job does not belong to project")
        ref = self.providers.regularized_dataset.resolve_sidecar_ref(project_id, job_id, sidecar_id)
        if ref is None:
            raise NotFoundError(f"Sidecar not found: {sidecar_id}")
        payload = self.providers.regularized_dataset.load_sidecar(project_id, job_id, ref)
        return dict(payload) if isinstance(payload, dict) else {"payload": payload}

    def get_job(self, project_id: str, job_id: str, user_context: AuthenticatedUserContext | None = None) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        state = self._load_state(job_id)
        if state["project_id"] != project_id:
            raise ValidationError("Job does not belong to project")
        return job_view(state)

    def list_outputs(self, project_id: str, job_id: str, user_context: AuthenticatedUserContext | None = None) -> dict[str, Any]:
        self._assert_project_access(project_id, user_context)
        state = self._load_state(job_id)
        if state["project_id"] != project_id:
            raise ValidationError("Job does not belong to project")
        return {
            "project_id": project_id,
            "job_id": job_id,
            "outputs": list(state.get("output_refs", [])),
        }

    def _assert_project_access(self, project_id: str, user_context: AuthenticatedUserContext | None = None) -> None:
        if user_context is None:
            return
        project = self.providers.repository.get_project(project_id, owner_user_id=user_context.user_id)
        if project is None:
            raise NotFoundError("Project not found")

    def _run_stage(
        self,
        state: dict[str, Any],
        stage: str,
        runner: Callable[[], Any],
    ) -> Any:
        cap = state.get("capability", {})
        cap_key = f"can_run_{stage}"
        if not cap.get(cap_key, True):
            set_stage(state, stage, "skipped")
            state["skipped_reasons"][stage] = f"capability {cap_key} is False"
            self._save_state(state)
            return {"status": "skipped", "reason": f"capability {cap_key} is False"}

        set_stage(state, stage, "processing")
        self._save_state(state)
        try:
            result = runner()
        except MarketMindError as exc:
            set_stage(state, stage, "failed", error=str(exc))
            self._save_state(state)
            raise _StageExecutionError(stage, exc) from exc
        except Exception as exc:
            wrapped = BusinessFlowError(f"Stage {stage} failed: {exc}")
            set_stage(state, stage, "failed", error=str(wrapped))
            self._save_state(state)
            raise _StageExecutionError(stage, wrapped) from exc

        refs = []
        if isinstance(result, dict):
            if result.get("status") == "skipped":
                set_stage(state, stage, "skipped", error=result.get("reason"))
                state["skipped_reasons"][stage] = result.get("reason", "")
                self._save_state(state)
                return result
            if "artifact_ref" in result and result["artifact_ref"]:
                refs.append(self._public_ref(result["artifact_ref"]))
            if "model_ref" in result and result["model_ref"]:
                refs.append(self._public_ref(result["model_ref"]))

        set_stage(state, stage, "completed", error=None, artifact_refs=refs)
        append_output_refs(state, refs)
        self._save_state(state)
        return result

    def _load_state(self, job_id: str) -> dict[str, Any]:
        payload = self.providers.analysis_models.load_model(job_id, JOB_STATE_MODEL_TYPE)
        if payload is None:
            raise NotFoundError(f"Analysis job not found: {job_id}")
        if not isinstance(payload, dict):
            raise BusinessFlowError(f"Invalid analysis job state: {job_id}")
        return dict(payload)

    def _save_state(self, state: dict[str, Any]) -> None:
        from backend.business.flows.data_processing_analysis_state import _now

        state["updated_at"] = _now()
        self.providers.analysis_models.save_model(
            str(state["job_id"]),
            JOB_STATE_MODEL_TYPE,
            state,
            metadata={"status": state.get("status", "queued")},
        )
        try:
            self.providers.analysis_event_stream.publish_event(
                build_data_processing_state_event(state)
            )
        except Exception:
            pass

    def _record_failure(self, state: dict[str, Any], stage_name: str, exc: Exception) -> None:
        message = str(exc) or exc.__class__.__name__
        state["status"] = "failed"
        state["error"] = message
        set_stage(state, stage_name, "failed", error=message)

    def _record_unhandled_failure(self, state: dict[str, Any], exc: Exception) -> None:
        failed_stage = self._stage_for_unhandled_failure(state)
        if isinstance(exc, MarketMindError):
            wrapped = exc
        else:
            wrapped = BusinessFlowError(f"Unhandled failure during {failed_stage}: {exc}")
        self._record_failure(state, failed_stage, wrapped)
        self._skip_stages_after(state, failed_stage)
        self._save_state(state)

    def _reset_job(self, state: dict[str, Any]) -> None:
        for stage in state["stages"]:
            stage["status"] = "queued"
            stage["error"] = None
            stage["artifact_refs"] = []
        state["quality"] = None
        state["capability"] = None
        state["output_refs"] = []
        state["skipped_reasons"] = {}
        state["error"] = None
        state["status"] = "queued"

    def _reset_analysis_stages(self, state: dict[str, Any]) -> None:
        for stage in state["stages"]:
            if stage["stage"] == "dataset_regularization":
                continue
            stage["status"] = "queued"
            stage["error"] = None
            stage["artifact_refs"] = []
        state["skipped_reasons"] = {}
        state["error"] = None

    def _skip_stages_after(self, state: dict[str, Any], failed_stage: str) -> None:
        failed_index = STAGE_NAMES.index(failed_stage)
        for stage in state["stages"]:
            if STAGE_NAMES.index(stage["stage"]) <= failed_index:
                continue
            stage["status"] = "skipped"
            stage["error"] = None
            stage["artifact_refs"] = []

    def _stage_for_unhandled_failure(self, state: dict[str, Any]) -> str:
        for stage in state["stages"]:
            if stage["status"] == "processing":
                return str(stage["stage"])
        completed = [
            stage["stage"]
            for stage in state["stages"]
            if stage["stage"] != "dataset_regularization" and stage["status"] == "completed"
        ]
        if completed:
            return str(completed[-1])
        return "overview"

    def _assert_ready_for_analysis(
        self, state: dict[str, Any], project_id: str, job_id: str
    ) -> None:
        if state.get("status") == "needs_review":
            raise ValidationError("Regularization needs review before analysis can run")

        reg_stage = next(
            (s for s in state.get("stages", []) if s.get("stage") == "dataset_regularization"),
            None,
        )
        if reg_stage is None or reg_stage.get("status") != "completed":
            raise ValidationError(
                "Dataset regularization must be completed before running analysis"
            )

        norm_ref = self.providers.regularized_dataset.resolve_dataset_ref(
            project_id, job_id, "normalized-dataset"
        )
        if norm_ref is None or norm_ref.type != "normalized_dataset":
            raise ValidationError("Normalized dataset is not available")

    @staticmethod
    def _validate_upload(filename: str, content: bytes) -> None:
        if not filename:
            raise ValidationError("Filename is required")
        if not content:
            raise ValidationError("Upload content is empty")
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        if ext not in {"csv", "xlsx", "xls"}:
            raise ValidationError("Upload must be CSV or Excel")

    @staticmethod
    def _public_ref(ref: Any) -> dict[str, Any]:
        if hasattr(ref, "__dict__"):
            return {k: v for k, v in ref.__dict__.items() if not k.startswith("_")}
        return dict(ref) if isinstance(ref, dict) else {"id": str(ref)}
