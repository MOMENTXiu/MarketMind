"""Contract tests for the PostgreSQL Retail Analysis state adapter."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine

from backend.infrastructure.adapters.postgres_retail_analysis_state_adapter import (
    MARKETER_INSIGHTS_RESULT_TYPE,
    RECOMMENDATIONS_RESULT_TYPE,
    RETAIL_RUN_TYPE,
    PostgresRetailAnalysisStateAdapter,
)
from backend.infrastructure.db import models  # noqa: F401
from backend.infrastructure.db.base import Base
from backend.infrastructure.db.models.analysis_result import AnalysisResultRecord
from backend.infrastructure.db.models.artifact import ArtifactRecord
from backend.infrastructure.db.models.dataset import DatasetRecord
from backend.infrastructure.db.models.processing_run import ProcessingRunRecord
from backend.infrastructure.db.models.project import ProjectRecord
from backend.infrastructure.db.models.uploaded_file import UploadedFileRecord
from backend.infrastructure.db.session import create_session_factory
from backend.providers.dtos import RetailAnalysisProjectStateDTO, RetailAnalysisRunInfoDTO


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def adapter(engine: Engine) -> PostgresRetailAnalysisStateAdapter:
    return PostgresRetailAnalysisStateAdapter(create_session_factory(engine))


def test_postgres_retail_analysis_state_adapter_contract(
    adapter: PostgresRetailAnalysisStateAdapter,
    engine: Engine,
) -> None:
    first = adapter.save_state(_state("project-1", "2026-05-27T09:00:00Z"))
    second = adapter.save_state(
        _state(
            "project-2",
            "2026-05-27T10:00:00Z",
            status="processing",
            run_info=_run_info("job-2", "trace-2", "processing", attempt=1),
            summary={"records": 12, "overridden": "project"},
        )
    )

    saved = adapter.save_run_info(
        "project-1",
        _run_info("job-1", "trace-1", "processing", attempt=1),
    )

    assert first.run_info is None
    assert second.run_info is not None
    assert saved is not None
    assert saved.run_info is not None
    assert adapter.get_state("project-1") == saved

    with create_session_factory(engine)() as session:
        project = session.get(ProjectRecord, "project-2")
        dataset = session.scalars(
            select(DatasetRecord).where(DatasetRecord.project_id == "project-2")
        ).one()
        latest_run = session.scalars(
            select(ProcessingRunRecord).where(
                ProcessingRunRecord.project_id == "project-2",
                ProcessingRunRecord.run_type == RETAIL_RUN_TYPE,
                ProcessingRunRecord.is_latest.is_(True),
            )
        ).one()
        project.metadata_json = {
            **project.metadata_json,
            "summary": {"records": 10, "base": True, "overridden": "project"},
        }
        assert dataset.schema_json["retail_analysis_state_adapter"] is True
        assert dataset.schema_json["public_ref"] == {
            "id": "dataset-1",
            "type": "dataset",
            "name": "retail_sales.csv",
            "url": None,
            "metadata": {},
        }
        assert dataset.quality_summary_json == {"grade": "A"}
        latest_run.result_summary_json = {"overridden": "run", "completed_stages": 3}
        session.commit()

    projects = adapter.list_projects()
    listed = projects[0]
    loaded_second = adapter.get_state("project-2")

    assert [project.id for project in projects] == ["project-2", "project-1"]
    assert loaded_second is not None
    assert loaded_second.summary == {
        "records": 10,
        "base": True,
        "overridden": "run",
        "completed_stages": 3,
    }
    assert listed.dataset_ref == {
        "id": "dataset-1",
        "type": "dataset",
        "name": "retail_sales.csv",
        "url": None,
        "metadata": {},
    }
    assert listed.dataset_filename == "retail_sales.csv"
    assert listed.quality_summary == {"grade": "A"}
    assert listed.artifact_refs == [
        {
            "id": "table-1",
            "type": "table",
            "name": "segments.csv",
            "url": "/api/analysis/projects/project-2/artifacts/table-1",
            "metadata": {"rows": 2},
        }
    ]
    assert listed.recommendations == [{"item": "milk", "score": 0.9}]
    assert listed.marketer_insights == {"segments": []}
    assert listed.stage_statuses == [{"stage": "dataset_preparation", "status": "queued"}]
    assert listed.job_id == "job-2"
    assert listed.trace_id == "trace-2"
    assert adapter.delete_project("project-2") is True
    assert adapter.delete_project("project-2") is False

    with create_session_factory(engine)() as session:
        assert session.get(ProjectRecord, "project-2") is None
        assert (
            session.scalars(
                select(ProcessingRunRecord).where(ProcessingRunRecord.project_id == "project-2")
            ).all()
            == []
        )
        assert (
            session.scalars(
                select(ArtifactRecord).where(ArtifactRecord.project_id == "project-2")
            ).all()
            == []
        )
        assert (
            session.scalars(
                select(AnalysisResultRecord).where(AnalysisResultRecord.project_id == "project-2")
            ).all()
            == []
        )


def test_postgres_retail_analysis_state_projection_prefers_db_dataset_rows(
    adapter: PostgresRetailAnalysisStateAdapter,
    engine: Engine,
) -> None:
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        session.add(
            ProjectRecord(
                id="project-db",
                name="DB Backed",
                description="db projection",
                status="completed",
                metadata_json={"summary": {"records": 20}},
                created_at=_dt("2026-05-27T11:00:00Z"),
                updated_at=_dt("2026-05-27T11:10:00Z"),
            )
        )
        session.add(
            UploadedFileRecord(
                id="upload-1",
                project_id="project-db",
                kind="retail_sales",
                filename="uploaded_sales.csv",
                storage_key="uploads/uploaded_sales.csv",
                storage_uri="file://uploads/uploaded_sales.csv",
                checksum=None,
                size_bytes=10,
                uploaded_at=_dt("2026-05-27T11:01:00Z"),
            )
        )
        session.flush()
        session.add(
            DatasetRecord(
                id="dataset-db",
                project_id="project-db",
                source_file_id="upload-1",
                dataset_type="clean",
                name="clean_sales.csv",
                storage_key="analysis/datasets/clean_sales.csv",
                storage_uri="file://analysis/datasets/clean_sales.csv",
                schema_json={"columns": ["user_id"]},
                row_count=20,
                column_count=4,
                quality_summary_json={"grade": "B"},
                created_at=_dt("2026-05-27T11:02:00Z"),
            )
        )
        session.add(
            ProcessingRunRecord(
                id="run-db",
                project_id="project-db",
                run_type=RETAIL_RUN_TYPE,
                status="completed",
                job_id="job-db",
                trace_id="trace-db",
                is_latest=True,
                attempt=2,
                stage_statuses_json={
                    "stage_statuses": [{"stage": "report", "status": "completed"}]
                },
                input_refs_json={"trigger": "retail_analysis_api", "metadata": {"source": "db"}},
                result_summary_json={"completed_stages": 1},
                error_json=None,
                started_at=_dt("2026-05-27T11:03:00Z"),
                finished_at=_dt("2026-05-27T11:04:00Z"),
                duration_ms=60000,
                created_at=_dt("2026-05-27T11:03:00Z"),
                updated_at=_dt("2026-05-27T11:04:00Z"),
            )
        )
        session.flush()
        session.add(
            ArtifactRecord(
                id="artifact-db",
                project_id="project-db",
                run_id="run-db",
                artifact_type="markdown",
                name="retail_analysis_report.md",
                storage_key="analysis/reports/retail_analysis_report.md",
                storage_uri="file://analysis/reports/retail_analysis_report.md",
                url="/api/analysis/projects/project-db/artifacts/report-1",
                metadata_json={
                    "public_ref": {
                        "id": "report-1",
                        "type": "markdown",
                        "name": "retail_analysis_report.md",
                        "url": "/api/analysis/projects/project-db/artifacts/report-1",
                        "metadata": {},
                    }
                },
                size_bytes=None,
                checksum=None,
                created_at=_dt("2026-05-27T11:05:00Z"),
                updated_at=_dt("2026-05-27T11:05:00Z"),
            )
        )
        session.add(
            AnalysisResultRecord(
                id="result-rec-1",
                project_id="project-db",
                run_id="run-db",
                result_type=RECOMMENDATIONS_RESULT_TYPE,
                payload_json={"recommendations": [{"item": "bread", "score": 0.8}]},
                created_at=_dt("2026-05-27T11:06:00Z"),
            )
        )
        session.add(
            AnalysisResultRecord(
                id="result-rec-2",
                project_id="project-db",
                run_id="run-db",
                result_type=MARKETER_INSIGHTS_RESULT_TYPE,
                payload_json={"marketer_insights": {"segments": [{"segment": "vip"}]}},
                created_at=_dt("2026-05-27T11:06:00Z"),
            )
        )
        session.commit()

    loaded = adapter.get_state("project-db")

    assert loaded is not None
    assert loaded.dataset_ref == {
        "id": "dataset-db",
        "type": "clean",
        "name": "uploaded_sales.csv",
        "url": "/api/analysis/projects/project-db/datasets/dataset-db",
        "metadata": {
            "storage_key": "analysis/datasets/clean_sales.csv",
            "storage_uri": "file://analysis/datasets/clean_sales.csv",
        },
    }
    assert loaded.quality_summary == {"grade": "B"}
    assert loaded.summary == {"records": 20, "completed_stages": 1}
    assert loaded.recommendations == [{"item": "bread", "score": 0.8}]
    assert loaded.marketer_insights == {"segments": [{"segment": "vip"}]}
    assert loaded.artifact_refs == [
        {
            "id": "report-1",
            "type": "markdown",
            "name": "retail_analysis_report.md",
            "url": "/api/analysis/projects/project-db/artifacts/report-1",
            "metadata": {},
        }
    ]
    assert loaded.run_info is not None
    assert loaded.run_info.attempt == 2
    assert loaded.run_info.metadata == {"source": "db"}


def _state(
    project_id: str,
    created_at: str,
    *,
    status: str = "queued",
    run_info: RetailAnalysisRunInfoDTO | None = None,
    summary: dict[str, object] | None = None,
) -> RetailAnalysisProjectStateDTO:
    return RetailAnalysisProjectStateDTO(
        id=project_id,
        name=f"Project {project_id}",
        description="contract state",
        status=status,
        stage_statuses=[{"stage": "dataset_preparation", "status": "queued"}],
        summary=summary or {"records": 0},
        dataset_ref={"id": "dataset-1", "type": "dataset", "name": "retail_sales.csv"},
        quality_summary={"grade": "A"},
        artifact_refs=[
            {
                "id": "table-1",
                "type": "table",
                "name": "segments.csv",
                "url": f"/api/analysis/projects/{project_id}/artifacts/table-1",
                "metadata": {"rows": 2},
            }
        ],
        recommendations=[{"item": "milk", "score": 0.9}],
        marketer_insights={"segments": []},
        run_info=run_info,
        created_at=created_at,
        updated_at=created_at,
    )


def _run_info(
    job_id: str,
    trace_id: str,
    status: str,
    *,
    attempt: int,
) -> RetailAnalysisRunInfoDTO:
    return RetailAnalysisRunInfoDTO(
        job_id=job_id,
        trace_id=trace_id,
        trigger="retail_analysis_api",
        attempt=attempt,
        status=status,
        created_at="2026-05-27T10:00:00Z",
        updated_at="2026-05-27T10:05:00Z",
        metadata={"source": "contract-test"},
    )


def _dt(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))
