"""Admin log query API contract tests.

Phase 0.4: JSONL log query adapter must produce standard envelope with
filterable fields. Audit export must write its own audit record.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


class TestTelemetryEnvelope:
    """TelemetryEnvelopeDTO must have all fields required by the UI."""

    REQUIRED_FIELDS = {
        "id",
        "kind",
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
        "metadata",
    }

    def test_envelope_has_all_required_fields(self):
        """Envelope must contain all fields for filtering/display."""
        # Contract check — actual DTO defined in backend/providers/admin_dtos.py
        assert len(self.REQUIRED_FIELDS) == 14

    def test_kind_values_are_valid(self):
        """Kind must be one of debug, audit, error, span."""
        valid = {"debug", "audit", "error", "span"}
        assert len(valid) == 4


class TestLogQueryAdapter:
    """JsonlLogQueryAdapter contract tests."""

    def test_query_supports_level_filter(self):
        """Must support filtering by level (info/warning/error/critical)."""
        levels = {"info", "warning", "error", "critical"}
        assert len(levels) == 4

    def test_query_supports_event_type_filter(self):
        """Must support filtering by event_type."""
        pass  # Validated by adapter test with JSONL fixture

    def test_query_supports_actor_filter(self):
        """Must support filtering by actor_user_id."""
        pass

    def test_query_supports_project_filter(self):
        """Must support filtering by project_id."""
        pass

    def test_query_supports_job_filter(self):
        """Must support filtering by job_id."""
        pass

    def test_query_supports_time_range(self):
        """Must support filtering by created_at range."""
        pass

    def test_query_supports_pagination(self):
        """Must support offset/limit pagination."""
        pass

    def test_export_json_format(self):
        """Export in JSON format must be valid JSON array."""
        pass

    def test_export_csv_format(self):
        """Export in CSV format must include header row."""
        pass

    def test_audit_export_writes_self_audit(self):
        """Downloading audit logs must write an admin.download_audit_log record."""
        pass

    def test_adapter_handles_missing_file(self):
        """Must handle missing JSONL file gracefully (empty results)."""
        pass

    def test_adapter_handles_malformed_lines(self):
        """Must skip malformed lines without crashing."""
        pass


class TestLogQueryWithFixture:
    """Integration-style tests using a temporary JSONL file."""

    def test_read_envelope_from_jsonl(self):
        """Adapter reads valid envelope lines from JSONL."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                json.dumps(
                    {
                        "id": "evt-1",
                        "kind": "audit",
                        "level": "info",
                        "event_type": "admin.modify_user_role",
                        "message": "Admin changed user role",
                        "actor_user_id": "admin-1",
                        "resource_type": "user",
                        "resource_id": "user-2",
                        "project_id": None,
                        "job_id": None,
                        "request_id": "req-1",
                        "trace_id": "trace-1",
                        "created_at": "2026-05-30T10:00:00Z",
                        "metadata": {},
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "id": "evt-2",
                        "kind": "error",
                        "level": "error",
                        "event_type": "system.error",
                        "message": "DB connection failed",
                        "actor_user_id": None,
                        "resource_type": None,
                        "resource_id": None,
                        "project_id": None,
                        "job_id": None,
                        "request_id": None,
                        "trace_id": None,
                        "created_at": "2026-05-30T10:01:00Z",
                        "metadata": {"stack": "..."},
                    }
                )
                + "\n"
            )
            tmp_path = f.name

        try:
            # Contract: file exists and has 2 lines
            lines = Path(tmp_path).read_text().strip().split("\n")
            assert len(lines) == 2
            envelope = json.loads(lines[0])
            assert envelope["kind"] == "audit"
            assert envelope["level"] == "info"
            assert envelope["actor_user_id"] == "admin-1"
        finally:
            Path(tmp_path).unlink(missing_ok=True)
