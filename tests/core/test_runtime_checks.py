"""Smoke tests for the runtime checks CLI.

Each command is invoked as a subprocess so the test exercises the same module
boundary as a production deployment self-test.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "backend.core.runtime_checks", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


HAPPY_PATH_COMMANDS: list[tuple[str, list[str], str]] = [
    ("check-config", [], "check-config: ok"),
    ("check-providers", [], "check-providers: ok"),
    ("check-storage", ["--sandbox"], "check-storage: ok"),
    ("check-analysis-artifacts", ["--sandbox"], "check-analysis-artifacts: ok"),
    ("check-retail-analysis", ["--sample"], "check-retail-analysis: ok"),
    (
        "check-analysis-optional-runtime",
        [],
        "check-analysis-optional-runtime: ok",
    ),
    (
        "check-retail-runtime",
        ["--dry-run"],
        "check-retail-runtime: ok",
    ),
    ("check-llm", ["--dry-run"], "check-llm: dry-run skipped"),
    ("validate-api-schemas", [], "validate-api-schemas: ok"),
    ("check-telemetry", [], "check-telemetry: ok"),
    ("check-audit-sink", [], "check-audit-sink: ok"),
    ("validate-log-schema", [], "validate-log-schema: ok"),
    ("validate-audit-schema", [], "validate-audit-schema: ok"),
    ("inspect-trace", ["--trace-id", "test"], "inspect-trace: skipped"),
    ("check-data-processing", ["--sample"], "check-data-processing: ok"),
    ("check-regularization", ["--sandbox"], "check-regularization: ok"),
]


@pytest.mark.parametrize(("command", "extra", "expected"), HAPPY_PATH_COMMANDS)
def test_command_happy_path(command: str, extra: list[str], expected: str) -> None:
    result = _run([command, *extra])
    assert result.returncode == 0, (
        f"command {command} failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert expected in result.stdout


def test_check_storage_requires_sandbox_flag() -> None:
    result = _run(["check-storage"])
    assert result.returncode == 1
    assert "refusing to run without --sandbox" in result.stdout


def test_check_analysis_artifacts_requires_sandbox_flag() -> None:
    result = _run(["check-analysis-artifacts"])
    assert result.returncode == 1
    assert "refusing to run without --sandbox" in result.stdout


def test_check_retail_analysis_requires_sample_flag() -> None:
    result = _run(["check-retail-analysis"])
    assert result.returncode == 1
    assert "refusing to run without --sample" in result.stdout


def test_check_llm_requires_dry_run_flag() -> None:
    result = _run(["check-llm"])
    assert result.returncode == 1
    assert "refusing to run without --dry-run" in result.stdout


def test_check_retail_runtime_requires_dry_run_flag() -> None:
    result = _run(["check-retail-runtime"])
    assert result.returncode == 1
    assert "refusing to run without --dry-run" in result.stdout


def test_check_data_processing_requires_sample_flag() -> None:
    result = _run(["check-data-processing"])
    assert result.returncode == 1
    assert "refusing to run without --sample" in result.stdout


def test_check_regularization_requires_sandbox_flag() -> None:
    result = _run(["check-regularization"])
    assert result.returncode == 1
    assert "refusing to run without --sandbox" in result.stdout


def test_validate_log_schema_missing_fixture_fails(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    result = _run(["validate-log-schema", "--fixture", str(missing)])
    assert result.returncode == 1
    assert "validate-log-schema: failed" in result.stdout


def test_unknown_command_exits_nonzero() -> None:
    result = _run(["not-a-command"])
    assert result.returncode != 0
