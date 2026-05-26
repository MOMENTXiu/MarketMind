"""Alembic migration roundtrip smoke test."""

# ruff: noqa: I001

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from alembic.command import downgrade, upgrade
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[3]
TABLES_IN_DOWNGRADE_ORDER = (
    "analysis_results",
    "artifacts",
    "processing_runs",
    "datasets",
    "uploaded_files",
    "projects",
    "alembic_version",
)


@pytest.fixture()
def alembic_config() -> Config:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set")

    _reset_database(database_url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_alembic_upgrade_downgrade_upgrade_roundtrip(alembic_config: Config) -> None:
    upgrade(alembic_config, "head")
    downgrade(alembic_config, "base")
    upgrade(alembic_config, "head")


def _reset_database(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            for table_name in TABLES_IN_DOWNGRADE_ORDER:
                connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
    finally:
        engine.dispose()
