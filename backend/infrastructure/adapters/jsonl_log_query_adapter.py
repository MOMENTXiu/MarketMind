"""JSONL log query adapter.

Reads structured telemetry envelopes from a JSONL file and supports
filtering, pagination, detail lookup, and JSON/CSV export.

Business layers access logs only through LogQueryProvider, not by
reading files directly.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from backend.providers.admin_dtos import (
    AdminLogPageDTO,
    AdminLogQueryDTO,
    AdminLogRecordDTO,
    ExportResultDTO,
)
from backend.providers.log_query_provider import LogQueryProvider


class JsonlLogQueryAdapter(LogQueryProvider):
    """Query and export events/audit logs from a JSONL file."""

    def __init__(self, log_path: str = "logs/telemetry/events.jsonl") -> None:
        self._log_path = Path(log_path)

    # ── Event log ─────────────────────────────────────────────────────────

    def list_events(self, query: AdminLogQueryDTO) -> AdminLogPageDTO:
        return self._query(query, kinds={"debug", "error", "span"})

    def get_event(self, event_id: str) -> AdminLogRecordDTO | None:
        return self._get_by_id(event_id)

    def export_events(self, query: AdminLogQueryDTO, fmt: str = "json") -> ExportResultDTO:
        result = self.list_events(query)
        return self._format_export(result.items, fmt, prefix="events")

    # ── Audit log ─────────────────────────────────────────────────────────

    def list_audit(self, query: AdminLogQueryDTO) -> AdminLogPageDTO:
        return self._query(query, kinds={"audit"})

    def get_audit(self, audit_id: str) -> AdminLogRecordDTO | None:
        return self._get_by_id(audit_id)

    def export_audit(self, query: AdminLogQueryDTO, fmt: str = "json") -> ExportResultDTO:
        result = self.list_audit(query)
        return self._format_export(result.items, fmt, prefix="audit")

    # ── Internals ─────────────────────────────────────────────────────────

    def _read_all(self) -> list[dict]:
        """Read all valid JSONL lines from the log file."""
        if not self._log_path.exists():
            return []
        records: list[dict] = []
        try:
            with open(self._log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue
        except Exception:
            return []
        return records

    def _matches(self, record: dict, query: AdminLogQueryDTO, kinds: set[str]) -> bool:
        """Check if a record matches the query filters."""
        rec_kind = record.get("kind", "")
        if kinds and rec_kind not in kinds:
            return False

        if query.kind is not None and record.get("kind") != query.kind:
            return False
        if query.level is not None and record.get("level") != query.level:
            return False
        if query.event_type is not None and record.get("event_type") != query.event_type:
            return False
        if query.actor_user_id is not None and record.get("actor_user_id") != query.actor_user_id:
            return False
        if query.project_id is not None and record.get("project_id") != query.project_id:
            return False
        if query.job_id is not None and record.get("job_id") != query.job_id:
            return False
        if query.request_id is not None and record.get("request_id") != query.request_id:
            return False
        if query.trace_id is not None and record.get("trace_id") != query.trace_id:
            return False

        created = record.get("created_at")
        if query.from_date and created and created < query.from_date:
            return False
        if query.to_date and created and created > query.to_date:
            return False

        return True

    def _record_to_dto(self, record: dict) -> AdminLogRecordDTO:
        return AdminLogRecordDTO(
            id=record.get("id", ""),
            level=record.get("level", "info"),
            event_type=record.get("event_type", ""),
            message=record.get("message", ""),
            actor_user_id=record.get("actor_user_id"),
            resource_type=record.get("resource_type"),
            resource_id=record.get("resource_id"),
            project_id=record.get("project_id"),
            job_id=record.get("job_id"),
            request_id=record.get("request_id"),
            trace_id=record.get("trace_id"),
            created_at=record.get("created_at"),
            metadata=record.get("metadata"),
        )

    def _query(self, query: AdminLogQueryDTO, kinds: set[str]) -> AdminLogPageDTO:
        all_records = self._read_all()
        matched = [r for r in all_records if self._matches(r, query, kinds)]
        total = len(matched)

        # Apply pagination
        start = max(0, query.offset)
        end = start + max(1, query.limit)
        page = matched[start:end]

        return AdminLogPageDTO(
            items=[self._record_to_dto(r) for r in page],
            total=total,
            offset=query.offset,
            limit=query.limit,
        )

    def _get_by_id(self, record_id: str) -> AdminLogRecordDTO | None:
        for record in self._read_all():
            if record.get("id") == record_id:
                return self._record_to_dto(record)
        return None

    def _format_export(
        self, items: list[AdminLogRecordDTO], fmt: str, prefix: str
    ) -> ExportResultDTO:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if fmt == "csv":
            output = io.StringIO()
            if items:
                writer = csv.DictWriter(
                    output,
                    fieldnames=[
                        "id",
                        "level",
                        "event_type",
                        "message",
                        "actor_user_id",
                        "resource_type",
                        "resource_id",
                        "project_id",
                        "job_id",
                        "request_id",
                        "trace_id",
                        "created_at",
                    ],
                )
                writer.writeheader()
                for item in items:
                    writer.writerow(
                        {
                            "id": item.id,
                            "level": item.level,
                            "event_type": item.event_type,
                            "message": item.message,
                            "actor_user_id": item.actor_user_id or "",
                            "resource_type": item.resource_type or "",
                            "resource_id": item.resource_id or "",
                            "project_id": item.project_id or "",
                            "job_id": item.job_id or "",
                            "request_id": item.request_id or "",
                            "trace_id": item.trace_id or "",
                            "created_at": item.created_at or "",
                        }
                    )
            content = output.getvalue()
            filename = f"{prefix}_{ts}.csv"
        else:
            content = json.dumps(
                [
                    {
                        "id": i.id,
                        "level": i.level,
                        "event_type": i.event_type,
                        "message": i.message,
                        "actor_user_id": i.actor_user_id,
                        "resource_type": i.resource_type,
                        "resource_id": i.resource_id,
                        "project_id": i.project_id,
                        "job_id": i.job_id,
                        "request_id": i.request_id,
                        "trace_id": i.trace_id,
                        "created_at": i.created_at,
                        "metadata": i.metadata,
                    }
                    for i in items
                ],
                ensure_ascii=False,
                indent=2,
            )
            filename = f"{prefix}_{ts}.json"

        return ExportResultDTO(
            content=content,
            format=fmt,
            filename=filename,
            record_count=len(items),
        )
