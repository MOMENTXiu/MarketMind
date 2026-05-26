"""Contract tests for the PostgreSQL project repository adapter."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.infrastructure.adapters.postgres_project_repository_adapter import (
    PostgresProjectRepositoryAdapter,
)
from backend.infrastructure.db import models  # noqa: F401
from backend.infrastructure.db.base import Base
from backend.infrastructure.db.session import create_session_factory
from backend.models.project import (
    AnalysisParameters,
    AnalysisResults,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set")

    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    _drop_alembic_version(engine)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        _drop_alembic_version(engine)
        engine.dispose()


@pytest.fixture()
def adapter(engine: Engine) -> PostgresProjectRepositoryAdapter:
    return PostgresProjectRepositoryAdapter(create_session_factory(engine))


def test_postgres_project_repository_contract(adapter: PostgresProjectRepositoryAdapter) -> None:
    first = adapter.create_project(ProjectCreate(name="First"))
    second = adapter.create_project(
        ProjectCreate(
            name="Second",
            description="with params",
            parameters=AnalysisParameters(min_support=0.05),
        )
    )

    assert adapter.count_projects() == 2
    assert adapter.get_project(first.id) is not None
    assert adapter.get_project(second.id).parameters.min_support == 0.05

    updated_first = adapter.update_project(
        first.id,
        ProjectUpdate(
            dataset_filename="sales.csv",
            dataset_path="file://projects/first/sales.csv",
        ),
    )
    assert updated_first is not None
    adapter.update_project(
        updated_first.id,
        ProjectUpdate(name="First Updated", parameters=AnalysisParameters(min_lift=1.2)),
    )

    projects = adapter.list_projects()
    assert [project.id for project in projects] == [second.id, first.id]
    assert [project.id for project in adapter.list_projects(skip=1, limit=1)] == [first.id]
    assert adapter.get_project(first.id).name == "First Updated"
    assert adapter.get_project(first.id).parameters.min_lift == 1.2

    results = AnalysisResults(
        association_rules=[{"antecedents": ["milk"], "consequents": ["bread"]}],
        charts={"overview": "/outputs/charts/overview.png"},
        report_path="/outputs/reports/report.md",
    )
    completed = adapter.mark_analysis_completed(first.id, results)
    assert completed is not None
    assert completed.status == ProjectStatus.COMPLETED
    assert completed.results == results
    assert completed.error_message is None

    failed = adapter.mark_analysis_failed(first.id, "boom")
    assert failed is not None
    assert failed.status == ProjectStatus.FAILED
    assert failed.error_message == "boom"

    assert adapter.delete_project(second.id) is True
    assert adapter.get_project(second.id) is None
    assert adapter.count_projects() == 1


def test_postgres_project_repository_missing_operations_return_current_values(
    adapter: PostgresProjectRepositoryAdapter,
) -> None:
    assert adapter.get_project("missing") is None
    assert adapter.update_project("missing", ProjectUpdate(name="Nope")) is None
    assert adapter.mark_analysis_completed("missing", AnalysisResults()) is None
    assert adapter.mark_analysis_failed("missing", "boom") is None
    assert adapter.delete_project("missing") is False


def _drop_alembic_version(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
