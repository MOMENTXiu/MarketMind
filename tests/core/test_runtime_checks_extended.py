"""Smoke tests for new runtime check commands."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "command,expected_code",
    [
        (["check-object-storage", "--sandbox"], 0),
        (["check-minio", "--sandbox"], 0),
        (["check-sample-files"], 0),
    ],
)
def test_runtime_check_commands(command: list[str], expected_code: int) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "backend.core.runtime_checks"] + command,
        capture_output=True,
        text=True,
    )
    assert result.returncode == expected_code, f"stderr: {result.stderr}\nstdout: {result.stdout}"
