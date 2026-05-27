"""Retail Analysis V2 flow orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from backend.business.flows.retail_analysis_state import (
    PROJECT_STATUSES,
    STAGE_NAMES,
    STAGE_STATUSES,
    build_analysis_state_event,
    empty_marketer_insights,
    new_stage,
    project_view,
    project_view_from_summary,
    public_ref,
    sanitize,
    state_from_provider_dto,
    state_to_provider_dto,
)
from backend.business.pipelines.retail_analysis_execution_pipeline import (
    RetailAnalysisExecutionPipeline,
)
from backend.business.pipelines.retail_dataset_preparation_pipeline import (
    RetailDatasetPreparationPipeline,
)
from backend.core.errors import (
    BusinessFlowError,
    InfrastructureError,
    MarketMindError,
    NotFoundError,
    ValidationError,
)
from backend.providers.container import ProvidersContainer
from backend.providers.dtos import AnalysisQueueJobPayloadDTO


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
            "run_info": None,
            "job_id": None,
            "trace_id": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        self._save_state(state)
        return project_view(state)

    def list_projects(self) -> dict[str, Any]:
        projects = [
            project_view_from_summary(project)
            for project in self.providers.retail_analysis_state.list_projects()
        ]
        projects.sort(key=lambda project: str(project.get("created_at") or ""), reverse=True)
        return {"projects": projects, "total": len(projects)}

    def delete_project(self, project_id: str) -> dict[str, Any]:
        self._load_state(project_id)
        deleted_models = 0
        legacy_model_types = {"retail_analysis_project_state"}
        for ref in self.providers.analysis_models.list_models(project_id):
            is_legacy_index = ref.model_type.startswith(
                "retail_analysis_project"
            ) and ref.model_type.endswith("index")
            if ref.model_type in legacy_model_types or is_legacy_index:
                continue
            if self.providers.analysis_models.delete_model(project_id, ref.model_type, ref.version):
                deleted_models += 1

        deleted = self.providers.retail_analysis_state.delete_project(project_id)
        return {"project_id": project_id, "deleted": deleted, "deleted_models": deleted_models}

    def upload_dataset(self, project_id: str, filename: str, content: bytes) -> dict[str, Any]:
        self._validate_csv_upload(filename, content)
        state = self._load_state(project_id)
        self._prepare_for_dataset_upload(state)
        self._save_state(state, "state_changed")

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
        self._save_state(state, "artifact_ready")
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
        attempt = self._next_attempt(state)
        now = _now()
        state["status"] = "processing"
        state["error"] = None
        state["run_info"] = {
            "job_id": job_id,
            "trace_id": trace_id,
            "trigger": "retail_analysis_api",
            "attempt": attempt,
            "status": "processing",
            "error": None,
            "created_at": now,
            "updated_at": now,
            "metadata": {"submitted_via": "retail_analysis_flow"},
        }
        self._sync_run_identifiers(state)
        self._reset_downstream_outputs(state, preserve_dataset_artifacts=True)
        self._save_state(state, "state_changed")

        payload = AnalysisQueueJobPayloadDTO(
            project_id=project_id,
            job_id=job_id,
            trace_id=trace_id,
            trigger="retail_analysis_api",
            attempt=attempt,
            submitted_at=state.get("updated_at"),
            metadata={"submitted_via": "retail_analysis_flow"},
        )
        try:
            self.providers.analysis_job_queue.enqueue_project_analysis(payload)
        except Exception as exc:
            self._record_queue_submission_failure(state, exc)
            self._save_state(state)
            raise InfrastructureError(
                str(state.get("error") or "Retail Analysis queue submission failed")
            ) from exc

        return {
            "project_id": project_id,
            "status": "processing",
            "job_id": job_id,
            "trace_id": trace_id,
        }

    def execute_scheduled_analysis(
        self,
        project_id: str,
        *,
        job_id: str | None = None,
        trace_id: str | None = None,
        attempt: int | None = None,
    ) -> None:
        try:
            state = self._load_state(project_id)
        except NotFoundError:
            return
        self._validate_scheduled_run(state, job_id=job_id, trace_id=trace_id, attempt=attempt)

        RetailAnalysisExecutionPipeline(
            self.providers,
            save_state=self._save_state,
            set_stage=self._set_stage,
            append_artifact_refs=self._append_artifact_refs,
            record_failure=self._record_failure,
            record_unhandled_execution_failure=self._record_unhandled_execution_failure,
            skip_stages_after=self._skip_stages_after,
        ).run(state)

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

    def get_artifact_payload(self, project_id: str, artifact_id: str) -> dict[str, Any]:
        state = self._load_state(project_id)
        ref = self._find_artifact_ref(state, artifact_id)
        if ref is None or ref.get("type") == "model":
            raise NotFoundError(f"Retail Analysis artifact not found: {artifact_id}")

        payload = self.providers.analysis_artifacts.load_payload(project_id, artifact_id)
        if payload is None:
            raise NotFoundError(f"Retail Analysis artifact not found: {artifact_id}")

        return {
            "project_id": project_id,
            "artifact": public_ref(payload.ref),
            "payload_type": payload.payload_type,
            "rows": sanitize(payload.rows or []),
            "payload": sanitize(payload.payload),
            "content": sanitize(payload.content),
        }

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

    def _load_state(self, project_id: str) -> dict[str, Any]:
        payload = self.providers.retail_analysis_state.get_state(project_id)
        if payload is None:
            raise NotFoundError(f"Retail Analysis project not found: {project_id}")
        return state_from_provider_dto(payload)

    def _save_state(self, state: dict[str, Any], event_name: str | None = None) -> None:
        status = str(state.get("status", "queued"))
        if status not in PROJECT_STATUSES:
            raise BusinessFlowError(f"Invalid Retail Analysis project status: {status}")
        state["updated_at"] = _now()
        saved_state = self.providers.retail_analysis_state.save_state(state_to_provider_dto(state))
        normalized = state_from_provider_dto(saved_state)
        state.clear()
        state.update(normalized)
        try:
            event = build_analysis_state_event(state, event=event_name)
            self.providers.analysis_event_stream.publish_event(event)
        except Exception:
            pass

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
        run_info = state.get("run_info")
        if isinstance(run_info, dict):
            run_info["status"] = "failed"
            run_info["error"] = message
            run_info["updated_at"] = _now()
        self._sync_run_identifiers(state)
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
        state["run_info"] = None
        self._sync_run_identifiers(state)
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

    def _record_queue_submission_failure(self, state: dict[str, Any], exc: Exception) -> None:
        message = f"Retail Analysis queue submission failed: {exc}"
        state["status"] = "failed"
        state["error"] = message
        run_info = state.get("run_info")
        if isinstance(run_info, dict):
            run_info["status"] = "failed"
            run_info["error"] = message
            run_info["updated_at"] = _now()
        self._sync_run_identifiers(state)
        state["summary"] = {**dict(state.get("summary", {})), "error": message}

    def _next_attempt(self, state: dict[str, Any]) -> int:
        run_info = state.get("run_info")
        if not isinstance(run_info, dict):
            return 1
        try:
            return max(int(run_info.get("attempt") or 0), 0) + 1
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _sync_run_identifiers(state: dict[str, Any]) -> None:
        run_info = state.get("run_info")
        if isinstance(run_info, dict):
            state["job_id"] = str(run_info.get("job_id")) if run_info.get("job_id") else None
            state["trace_id"] = str(run_info.get("trace_id")) if run_info.get("trace_id") else None
            return
        state["job_id"] = None
        state["trace_id"] = None

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

    @staticmethod
    def _validate_scheduled_run(
        state: dict[str, Any],
        *,
        job_id: str | None,
        trace_id: str | None,
        attempt: int | None,
    ) -> None:
        if job_id is None and trace_id is None and attempt is None:
            return
        if state.get("status") != "processing":
            raise ValidationError("Retail Analysis scheduled execution requires processing state")

        run_info = state.get("run_info")
        if not isinstance(run_info, dict):
            raise ValidationError("Retail Analysis scheduled execution has no run metadata")
        expected_attempt = _optional_int(run_info.get("attempt"))
        actual_attempt = _optional_int(attempt)
        if (
            (job_id is not None and str(run_info.get("job_id") or "") != job_id)
            or (trace_id is not None and str(run_info.get("trace_id") or "") != trace_id)
            or (attempt is not None and expected_attempt != actual_attempt)
        ):
            raise ValidationError("Retail Analysis worker payload does not match latest run")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
