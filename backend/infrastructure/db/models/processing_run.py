"""Processing run lifecycle metadata table model."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.db.base import Base


class ProcessingRunRecord(Base):
    __tablename__ = "processing_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    job_id: Mapped[str | None] = mapped_column(String(64), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64))
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_statuses_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    input_refs_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
