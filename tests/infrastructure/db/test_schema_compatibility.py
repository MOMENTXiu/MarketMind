"""Schema compatibility guards for PostgreSQL/openGauss-friendly migrations."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import JSON

from backend.infrastructure.db import models  # noqa: F401
from backend.infrastructure.db.base import Base

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "alembic" / "versions" / "0001_initial_schema.py"
EXPECTED_TABLES = {
    "projects",
    "uploaded_files",
    "datasets",
    "processing_runs",
    "artifacts",
    "analysis_results",
}
FORBIDDEN_MIGRATION_TOKENS = (
    "pgcrypto",
    "gen_random_uuid",
    "uuid_generate_v4",
    "JSONB",
    "@>",
    "#>",
    "?",
    "?&",
    "?|",
    "postgresql_where",
    "postgresql_using",
    "postgresql_ops",
)


def test_metadata_contains_only_first_pr_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_json_columns_use_sqlalchemy_logical_json_type() -> None:
    json_columns = [
        column
        for table in Base.metadata.tables.values()
        for column in table.columns
        if column.name.endswith("_json") or column.name == "payload_json"
    ]

    assert json_columns
    assert all(isinstance(column.type, JSON) for column in json_columns)


def test_primary_keys_use_application_generated_strings() -> None:
    for table in Base.metadata.tables.values():
        primary_key = list(table.primary_key.columns)
        assert len(primary_key) == 1
        assert primary_key[0].name == "id"
        assert primary_key[0].server_default is None
        assert primary_key[0].default is None


def test_initial_migration_avoids_postgresql_specific_features() -> None:
    migration_source = MIGRATION.read_text(encoding="utf-8")
    violations = [token for token in FORBIDDEN_MIGRATION_TOKENS if token in migration_source]

    assert violations == []
