"""PostgreSQL-backed Retail V2 state adapter."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.errors import InfrastructureError
from backend.infrastructure.db.models.analysis_result import AnalysisResultRecord
from backend.infrastructure.db.models.artifact import ArtifactRecord
from backend.infrastructure.db.models.dataset import DatasetRecord
from backend.infrastructure.db.models.processing_run import ProcessingRunRecord
from backend.infrastructure.db.models.project import ProjectRecord
from backend.infrastructure.db.models.uploaded_file import UploadedFileRecord
from backend.providers.dtos import (
    RetailAnalysisProjectStateDTO,
    RetailAnalysisProjectSummaryDTO,
    RetailAnalysisRunInfoDTO,
)

SessionFactory = Callable[[], Session]

DEFAULT_STAGE_NAMES = (
    "dataset_preparation",
    "feature_engineering",
    "segmentation",
    "association",
    "recommendation",
    "marketer_insights",
    "report",
)
RETAIL_RUN_TYPE = "retail_analysis"
RECOMMENDATIONS_RESULT_TYPE = "retail_recommendations"
MARKETER_INSIGHTS_RESULT_TYPE = "retail_marketer_insights"


class PostgresRetailAnalysisStateAdapter:
    """RetailAnalysisStateProvider backed by the existing six-table schema."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def save_state(self, state: RetailAnalysisProjectStateDTO) -> RetailAnalysisProjectStateDTO:
        try:
            with self._session_factory() as session:
                with session.begin():
                    project = session.get(ProjectRecord, state.id)
                    if project is None:
                        project = ProjectRecord(
                            id=state.id,
                            name=state.name,
                            description=state.description,
                            status=state.status,
                            metadata_json={},
                            created_at=_parse_datetime(state.created_at),
                            updated_at=_parse_datetime(state.updated_at, state.created_at),
                        )
                        session.add(project)

                    self._apply_project_record(project, state)
                    session.flush()
                    self._sync_dataset_ref(session, state)
                    latest_run = self._upsert_latest_run(session, state)
                    session.flush()
                    self._sync_artifact_refs(session, state, latest_run)
                    self._replace_analysis_results(session, state, latest_run)

            saved = self.get_state(state.id)
            if saved is None:
                raise InfrastructureError(f"Failed to persist Retail Analysis state: {state.id}")
            return saved
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                f"Failed to persist Retail Analysis state: {state.id}"
            ) from exc

    def get_state(self, project_id: str) -> RetailAnalysisProjectStateDTO | None:
        try:
            with self._session_factory() as session:
                project = session.get(ProjectRecord, project_id)
                if project is None:
                    return None

                latest_run = self._latest_run(session, project_id)
                dataset = self._latest_dataset(session, project_id)
                uploaded_file = self._source_upload(session, project_id, dataset)
                artifact_records = self._artifact_records(session, project_id, latest_run)
                result_records = self._analysis_result_records(session, project_id, latest_run)
                return self._state_from_projection(
                    project,
                    latest_run,
                    dataset,
                    uploaded_file,
                    artifact_records,
                    result_records,
                )
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                f"Failed to load Retail Analysis state: {project_id}"
            ) from exc

    def save_run_info(
        self,
        project_id: str,
        run_info: RetailAnalysisRunInfoDTO,
    ) -> RetailAnalysisProjectStateDTO | None:
        current = self.get_state(project_id)
        if current is None:
            return None

        updated = replace(
            current,
            status=run_info.status,
            run_info=run_info,
            error=run_info.error,
            updated_at=run_info.updated_at or current.updated_at,
        )
        return self.save_state(updated)

    def list_projects(self) -> list[RetailAnalysisProjectSummaryDTO]:
        try:
            with self._session_factory() as session:
                projects = session.scalars(
                    select(ProjectRecord).order_by(ProjectRecord.created_at.desc())
                ).all()
                summaries: list[RetailAnalysisProjectSummaryDTO] = []
                for project in projects:
                    latest_run = self._latest_run(session, project.id)
                    dataset = self._latest_dataset(session, project.id)
                    uploaded_file = self._source_upload(session, project.id, dataset)
                    artifacts = self._artifact_records(session, project.id, latest_run)
                    results = self._analysis_result_records(session, project.id, latest_run)
                    state = self._state_from_projection(
                        project,
                        latest_run,
                        dataset,
                        uploaded_file,
                        artifacts,
                        results,
                    )
                    summaries.append(_summary_from_state(state))
                return summaries
        except SQLAlchemyError as exc:
            raise InfrastructureError("Failed to list Retail Analysis state") from exc

    def delete_project(self, project_id: str) -> bool:
        try:
            with self._session_factory() as session:
                with session.begin():
                    project = session.get(ProjectRecord, project_id)
                    if project is None:
                        return False
                    session.delete(project)
                    return True
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                f"Failed to delete Retail Analysis state: {project_id}"
            ) from exc

    @staticmethod
    def _apply_project_record(project: ProjectRecord, state: RetailAnalysisProjectStateDTO) -> None:
        metadata = dict(project.metadata_json or {})
        metadata["summary"] = _json_object(state.summary)
        metadata["dataset_ref"] = _json_or_none(state.dataset_ref)
        metadata["quality_summary"] = _json_object(state.quality_summary)
        metadata["error"] = state.error
        metadata["retail_analysis_state_adapter"] = True

        project.name = state.name
        project.description = state.description
        project.status = state.status
        project.metadata_json = metadata
        project.created_at = _parse_datetime(state.created_at)
        project.updated_at = _parse_datetime(state.updated_at, state.created_at)

    def _upsert_latest_run(
        self,
        session: Session,
        state: RetailAnalysisProjectStateDTO,
    ) -> ProcessingRunRecord | None:
        latest_runs = session.scalars(
            select(ProcessingRunRecord)
            .where(
                ProcessingRunRecord.project_id == state.id,
                ProcessingRunRecord.run_type == RETAIL_RUN_TYPE,
                ProcessingRunRecord.is_latest.is_(True),
            )
            .order_by(ProcessingRunRecord.created_at.desc())
        ).all()
        if not latest_runs and not _should_materialize_run(state):
            return None

        run_info = state.run_info
        chosen = _select_matching_latest_run(latest_runs, run_info)
        for latest_run in latest_runs:
            latest_run.is_latest = latest_run is chosen

        if chosen is None:
            chosen = ProcessingRunRecord(
                id=str(uuid4()),
                project_id=state.id,
                run_type=RETAIL_RUN_TYPE,
                status=state.status,
                job_id=None,
                trace_id=None,
                is_latest=True,
                attempt=run_info.attempt if run_info is not None else 0,
                stage_statuses_json={},
                input_refs_json={},
                result_summary_json={},
                error_json=None,
                started_at=None,
                finished_at=None,
                duration_ms=None,
                created_at=_parse_datetime(
                    run_info.created_at if run_info is not None else state.created_at
                ),
                updated_at=_parse_datetime(
                    run_info.updated_at if run_info is not None else state.updated_at,
                    run_info.created_at if run_info is not None else state.created_at,
                ),
            )
            session.add(chosen)

        chosen.is_latest = True
        chosen.status = run_info.status if run_info is not None else state.status
        chosen.job_id = run_info.job_id if run_info is not None else None
        chosen.trace_id = run_info.trace_id if run_info is not None else None
        chosen.attempt = run_info.attempt if run_info is not None else chosen.attempt
        chosen.stage_statuses_json = {"stage_statuses": _json_list(state.stage_statuses)}
        chosen.input_refs_json = {
            "trigger": run_info.trigger if run_info is not None else None,
            "metadata": _json_object(run_info.metadata if run_info is not None else {}),
        }
        chosen.result_summary_json = _json_object(state.summary)
        chosen.error_json = _error_payload(run_info.error if run_info is not None else state.error)
        chosen.started_at = _parse_datetime(
            run_info.created_at if run_info is not None else state.updated_at,
            state.created_at,
        )
        chosen.finished_at = _finished_at(
            run_info.updated_at if run_info is not None else state.updated_at,
            chosen.status,
        )
        chosen.duration_ms = _duration_ms(chosen.started_at, chosen.finished_at)
        chosen.created_at = chosen.created_at or _parse_datetime(state.created_at)
        chosen.updated_at = _parse_datetime(
            run_info.updated_at if run_info is not None else state.updated_at,
            run_info.created_at if run_info is not None else state.created_at,
        )
        return chosen

    def _sync_artifact_refs(
        self,
        session: Session,
        state: RetailAnalysisProjectStateDTO,
        latest_run: ProcessingRunRecord | None,
    ) -> None:
        existing_records = session.scalars(
            select(ArtifactRecord)
            .where(ArtifactRecord.project_id == state.id)
            .order_by(ArtifactRecord.created_at.asc())
        ).all()
        by_key = {(record.artifact_type, record.name): record for record in existing_records}
        managed_by_key = {
            key: record
            for key, record in by_key.items()
            if bool((record.metadata_json or {}).get("retail_analysis_state_adapter"))
        }

        keep_keys: set[tuple[str, str]] = set()
        updated_at = _parse_datetime(state.updated_at, state.created_at)
        for ref in state.artifact_refs:
            public_ref = _public_ref_dict(ref)
            artifact_type = str(public_ref.get("type") or "artifact")
            name = str(public_ref.get("name") or public_ref.get("id") or "artifact")
            key = (artifact_type, name)
            keep_keys.add(key)
            record = by_key.get(key)
            if record is None:
                record = ArtifactRecord(
                    id=_stable_uuid("artifact", state.id, artifact_type, name),
                    project_id=state.id,
                    run_id=latest_run.id if latest_run is not None else None,
                    artifact_type=artifact_type,
                    name=name,
                    storage_key=f"retail-analysis/{state.id}/{public_ref.get('id') or name}",
                    storage_uri=str(public_ref.get("url") or ""),
                    url=None,
                    metadata_json={},
                    size_bytes=None,
                    checksum=None,
                    created_at=updated_at,
                    updated_at=updated_at,
                )
                session.add(record)

            metadata = dict(record.metadata_json or {})
            metadata["retail_analysis_state_adapter"] = True
            metadata["public_id"] = str(public_ref.get("id") or record.id)
            metadata["public_ref"] = public_ref
            metadata["metadata"] = _json_object(public_ref.get("metadata") or {})
            record.run_id = latest_run.id if latest_run is not None else None
            record.artifact_type = artifact_type
            record.name = name
            record.storage_key = str(
                metadata["metadata"].get("storage_key")
                or f"retail-analysis/{state.id}/{metadata['public_id']}"
            )
            record.storage_uri = str(
                public_ref.get("url")
                or metadata["metadata"].get("storage_uri")
                or f"/api/analysis/projects/{state.id}/artifacts/{metadata['public_id']}"
            )
            record.url = str(public_ref.get("url")) if public_ref.get("url") else None
            record.metadata_json = metadata
            record.updated_at = updated_at

        for key, record in managed_by_key.items():
            if key not in keep_keys:
                session.delete(record)

    def _sync_dataset_ref(self, session: Session, state: RetailAnalysisProjectStateDTO) -> None:
        managed_records = session.scalars(
            select(DatasetRecord).where(DatasetRecord.project_id == state.id)
        ).all()
        managed_records = [
            record
            for record in managed_records
            if bool((record.schema_json or {}).get("retail_analysis_state_adapter"))
        ]
        if state.dataset_ref is None:
            for record in managed_records:
                session.delete(record)
            return

        public_ref = _public_ref_dict(state.dataset_ref)
        public_id = str(public_ref.get("id") or "dataset")
        record_id = _stable_uuid("dataset", state.id, public_id)
        record = session.get(DatasetRecord, record_id)
        if record is None or record.project_id != state.id:
            record = DatasetRecord(
                id=record_id,
                project_id=state.id,
                source_file_id=None,
                dataset_type=str(public_ref.get("type") or "retail_dataset"),
                name=str(public_ref.get("name") or public_id),
                storage_key="",
                storage_uri="",
                schema_json={},
                row_count=None,
                column_count=None,
                quality_summary_json={},
                created_at=_parse_datetime(state.updated_at, state.created_at),
            )
            session.add(record)

        metadata = _json_object(public_ref.get("metadata") or {})
        record.dataset_type = str(public_ref.get("type") or record.dataset_type)
        record.name = str(public_ref.get("name") or record.name)
        record.storage_key = str(
            metadata.get("storage_key") or f"retail-analysis/{state.id}/datasets/{public_id}"
        )
        record.storage_uri = str(
            metadata.get("storage_uri") or public_ref.get("url") or record.storage_key
        )
        record.schema_json = {
            "retail_analysis_state_adapter": True,
            "public_id": public_id,
            "public_ref": public_ref,
        }
        record.quality_summary_json = _json_object(state.quality_summary)

        for managed_record in managed_records:
            if managed_record.id != record.id:
                session.delete(managed_record)

    def _replace_analysis_results(
        self,
        session: Session,
        state: RetailAnalysisProjectStateDTO,
        latest_run: ProcessingRunRecord | None,
    ) -> None:
        session.execute(
            delete(AnalysisResultRecord).where(
                AnalysisResultRecord.project_id == state.id,
                AnalysisResultRecord.result_type.in_(
                    [RECOMMENDATIONS_RESULT_TYPE, MARKETER_INSIGHTS_RESULT_TYPE]
                ),
            )
        )

        created_at = _parse_datetime(state.updated_at, state.created_at)
        session.add(
            AnalysisResultRecord(
                id=str(uuid4()),
                project_id=state.id,
                run_id=latest_run.id if latest_run is not None else None,
                result_type=RECOMMENDATIONS_RESULT_TYPE,
                payload_json={"recommendations": _json_list(state.recommendations)},
                created_at=created_at,
            )
        )
        session.add(
            AnalysisResultRecord(
                id=str(uuid4()),
                project_id=state.id,
                run_id=latest_run.id if latest_run is not None else None,
                result_type=MARKETER_INSIGHTS_RESULT_TYPE,
                payload_json={"marketer_insights": _json_object(state.marketer_insights)},
                created_at=created_at,
            )
        )

    @staticmethod
    def _latest_run(session: Session, project_id: str) -> ProcessingRunRecord | None:
        return session.scalars(
            select(ProcessingRunRecord)
            .where(
                ProcessingRunRecord.project_id == project_id,
                ProcessingRunRecord.run_type == RETAIL_RUN_TYPE,
                ProcessingRunRecord.is_latest.is_(True),
            )
            .order_by(ProcessingRunRecord.updated_at.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _latest_dataset(session: Session, project_id: str) -> DatasetRecord | None:
        return session.scalars(
            select(DatasetRecord)
            .where(DatasetRecord.project_id == project_id)
            .order_by(DatasetRecord.created_at.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _source_upload(
        session: Session,
        project_id: str,
        dataset: DatasetRecord | None,
    ) -> UploadedFileRecord | None:
        if dataset is not None and dataset.source_file_id:
            upload = session.get(UploadedFileRecord, dataset.source_file_id)
            if upload is not None:
                return upload

        return session.scalars(
            select(UploadedFileRecord)
            .where(UploadedFileRecord.project_id == project_id)
            .order_by(UploadedFileRecord.uploaded_at.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _artifact_records(
        session: Session,
        project_id: str,
        latest_run: ProcessingRunRecord | None,
    ) -> Sequence[ArtifactRecord]:
        records = session.scalars(
            select(ArtifactRecord)
            .where(ArtifactRecord.project_id == project_id)
            .order_by(ArtifactRecord.created_at.asc())
        ).all()
        if latest_run is None:
            return records
        filtered = [record for record in records if record.run_id in {None, latest_run.id}]
        return filtered or records

    @staticmethod
    def _analysis_result_records(
        session: Session,
        project_id: str,
        latest_run: ProcessingRunRecord | None,
    ) -> Sequence[AnalysisResultRecord]:
        records = session.scalars(
            select(AnalysisResultRecord)
            .where(AnalysisResultRecord.project_id == project_id)
            .order_by(AnalysisResultRecord.created_at.desc())
        ).all()
        if latest_run is None:
            return records
        filtered = [record for record in records if record.run_id in {None, latest_run.id}]
        return filtered or records

    @staticmethod
    def _state_from_projection(
        project: ProjectRecord,
        latest_run: ProcessingRunRecord | None,
        dataset: DatasetRecord | None,
        uploaded_file: UploadedFileRecord | None,
        artifact_records: Sequence[ArtifactRecord],
        result_records: Sequence[AnalysisResultRecord],
    ) -> RetailAnalysisProjectStateDTO:
        metadata = dict(project.metadata_json or {})
        summary = {
            **_json_object(metadata.get("summary") or {}),
            **_json_object(latest_run.result_summary_json if latest_run is not None else {}),
        }
        run_info = _run_info_from_record(latest_run)
        error = _error_message(
            latest_run.error_json if latest_run is not None else None
        ) or metadata.get("error")

        return RetailAnalysisProjectStateDTO(
            id=project.id,
            name=project.name,
            description=project.description or "",
            status=latest_run.status if latest_run is not None else project.status,
            stage_statuses=_stage_statuses_from_run(latest_run),
            summary=summary,
            dataset_ref=_dataset_ref(project, dataset, uploaded_file),
            quality_summary=_quality_summary(project, dataset),
            artifact_refs=[_artifact_public_ref(record) for record in artifact_records],
            recommendations=_recommendations_payload(result_records),
            marketer_insights=_marketer_insights_payload(result_records),
            run_info=run_info,
            error=str(error) if error else None,
            created_at=_isoformat(project.created_at),
            updated_at=_isoformat(project.updated_at),
        )


def _summary_from_state(state: RetailAnalysisProjectStateDTO) -> RetailAnalysisProjectSummaryDTO:
    job_id = state.run_info.job_id if state.run_info is not None else None
    trace_id = state.run_info.trace_id if state.run_info is not None else None
    dataset_filename = None
    if isinstance(state.dataset_ref, dict):
        name = state.dataset_ref.get("name")
        dataset_filename = str(name) if name else None

    return RetailAnalysisProjectSummaryDTO(
        id=state.id,
        name=state.name,
        description=state.description,
        status=state.status,
        dataset_ref=state.dataset_ref,
        dataset_filename=dataset_filename,
        quality_summary=state.quality_summary,
        artifact_refs=state.artifact_refs,
        recommendations=state.recommendations,
        marketer_insights=state.marketer_insights,
        stage_statuses=state.stage_statuses,
        summary=state.summary,
        job_id=job_id,
        trace_id=trace_id,
        run_info=state.run_info,
        error=state.error,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


def _dataset_ref(
    project: ProjectRecord,
    dataset: DatasetRecord | None,
    uploaded_file: UploadedFileRecord | None,
) -> dict[str, Any] | None:
    if dataset is None:
        metadata_ref = (project.metadata_json or {}).get("dataset_ref")
        return _public_ref_dict(metadata_ref) if isinstance(metadata_ref, dict) else None
    schema = dict(dataset.schema_json or {})
    public_ref = schema.get("public_ref")
    if isinstance(public_ref, dict):
        return _public_ref_dict(public_ref)
    name = uploaded_file.filename if uploaded_file is not None else dataset.name
    url = f"/api/analysis/projects/{project.id}/datasets/{dataset.id}"
    return _public_ref_dict(
        {
            "id": dataset.id,
            "type": dataset.dataset_type,
            "name": name,
            "url": url,
            "metadata": {
                "storage_key": dataset.storage_key,
                "storage_uri": dataset.storage_uri,
            },
        }
    )


def _quality_summary(project: ProjectRecord, dataset: DatasetRecord | None) -> dict[str, Any]:
    if dataset is not None and dataset.quality_summary_json:
        return _json_object(dataset.quality_summary_json)
    return _json_object((project.metadata_json or {}).get("quality_summary") or {})


def _artifact_public_ref(record: ArtifactRecord) -> dict[str, Any]:
    metadata = dict(record.metadata_json or {})
    public_ref = metadata.get("public_ref")
    if isinstance(public_ref, dict):
        return _public_ref_dict(public_ref)
    return _public_ref_dict(
        {
            "id": metadata.get("public_id") or record.id,
            "type": record.artifact_type,
            "name": record.name,
            "url": record.url,
            "metadata": metadata.get("metadata") or {},
        }
    )


def _recommendations_payload(records: Sequence[AnalysisResultRecord]) -> list[dict[str, Any]]:
    for record in records:
        if record.result_type == RECOMMENDATIONS_RESULT_TYPE:
            payload = record.payload_json or {}
            recommendations = (
                payload.get("recommendations") if isinstance(payload, dict) else payload
            )
            return _json_list(recommendations or [])
    return []


def _marketer_insights_payload(records: Sequence[AnalysisResultRecord]) -> dict[str, Any]:
    for record in records:
        if record.result_type == MARKETER_INSIGHTS_RESULT_TYPE:
            payload = record.payload_json or {}
            insights = payload.get("marketer_insights") if isinstance(payload, dict) else payload
            return _json_object(insights or {})
    return {}


def _stage_statuses_from_run(latest_run: ProcessingRunRecord | None) -> list[dict[str, Any]]:
    if latest_run is None:
        return _default_stage_statuses()
    payload = latest_run.stage_statuses_json or {}
    if isinstance(payload, dict) and isinstance(payload.get("stage_statuses"), list):
        return _json_list(payload.get("stage_statuses") or [])
    return _default_stage_statuses()


def _run_info_from_record(
    latest_run: ProcessingRunRecord | None,
) -> RetailAnalysisRunInfoDTO | None:
    if latest_run is None:
        return None

    input_refs = latest_run.input_refs_json or {}
    trigger = input_refs.get("trigger") if isinstance(input_refs, dict) else None
    has_visible_run = bool(
        latest_run.job_id or latest_run.trace_id or trigger or latest_run.attempt > 0
    )
    if not has_visible_run:
        return None

    return RetailAnalysisRunInfoDTO(
        job_id=latest_run.job_id or "",
        trace_id=latest_run.trace_id or "",
        trigger=str(trigger or "retail_analysis_api"),
        attempt=latest_run.attempt,
        status=latest_run.status,
        error=_error_message(latest_run.error_json),
        created_at=_isoformat(latest_run.created_at),
        updated_at=_isoformat(latest_run.updated_at),
        metadata=_json_object(input_refs.get("metadata") if isinstance(input_refs, dict) else {}),
    )


def _default_stage_statuses() -> list[dict[str, Any]]:
    return [
        {
            "stage": stage_name,
            "status": "queued",
            "error": None,
            "artifact_refs": [],
        }
        for stage_name in DEFAULT_STAGE_NAMES
    ]


def _should_materialize_run(state: RetailAnalysisProjectStateDTO) -> bool:
    return any(
        [
            state.run_info is not None,
            state.dataset_ref is not None,
            bool(state.summary),
            bool(state.error),
            state.status != "queued",
            _json_list(state.stage_statuses) != _default_stage_statuses(),
        ]
    )


def _select_matching_latest_run(
    latest_runs: Sequence[ProcessingRunRecord],
    run_info: RetailAnalysisRunInfoDTO | None,
) -> ProcessingRunRecord | None:
    if not latest_runs:
        return None
    if run_info is None:
        return latest_runs[0]

    for latest_run in latest_runs:
        if latest_run.job_id and latest_run.job_id == run_info.job_id:
            return latest_run
        if latest_run.trace_id and latest_run.trace_id == run_info.trace_id:
            return latest_run
    for latest_run in latest_runs:
        if (
            not latest_run.job_id
            and not latest_run.trace_id
            and latest_run.attempt in {0, run_info.attempt}
        ):
            return latest_run
    return None


def _stable_uuid(namespace: str, *parts: str) -> str:
    seed = ":".join([namespace, *parts])
    return str(uuid5(NAMESPACE_URL, seed))


def _parse_datetime(value: str | None, fallback: str | None = None) -> datetime:
    candidate = value or fallback
    if candidate:
        normalized = candidate.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return datetime.now(UTC)


def _finished_at(value: str | None, status: str) -> datetime | None:
    if status not in {"completed", "failed"}:
        return None
    return _parse_datetime(value)


def _duration_ms(started_at: datetime | None, finished_at: datetime | None) -> int | None:
    if started_at is None or finished_at is None:
        return None
    delta = finished_at - started_at
    return max(int(delta.total_seconds() * 1000), 0)


def _isoformat(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def _error_payload(message: str | None) -> dict[str, Any] | None:
    if not message:
        return None
    return {"message": message}


def _error_message(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    message = payload.get("message")
    return str(message) if message else None


def _public_ref_dict(ref: Any) -> dict[str, Any]:
    payload = dict(ref or {}) if isinstance(ref, dict) else {}
    return {
        "id": _json_scalar(payload.get("id")),
        "type": _json_scalar(payload.get("type")),
        "name": _json_scalar(payload.get("name")),
        "url": _json_scalar(payload.get("url")),
        "metadata": _json_object(payload.get("metadata") or {}),
    }


def _json_scalar(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_or_none(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return _json_object(value)


def _json_object(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    return json.loads(json.dumps(value, ensure_ascii=False))


def _json_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    return json.loads(json.dumps(value, ensure_ascii=False))
