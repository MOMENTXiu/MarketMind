"""Controller thinness guard: API layer must not import legacy SDK/business deps."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "backend" / "api"

CONTROLLER_FILES: tuple[str, ...] = (
    "projects.py",
    "recommend.py",
    "association.py",
    "voice.py",
    "ai_voice.py",
)

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "backend.services",
    "backend.core.storage",
    "backend.core.recommend",
    "backend.infrastructure",
    "edge_tts",
    "httpx",
    "pandas",
    "sklearn",
    "mlxtend",
    "shutil",
)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _is_forbidden(module: str) -> bool:
    return any(module == p or module.startswith(f"{p}.") for p in FORBIDDEN_PREFIXES)


@pytest.mark.parametrize("filename", CONTROLLER_FILES)
def test_controller_does_not_import_forbidden_modules(filename: str) -> None:
    path = API_DIR / filename
    violations = [module for module in _imported_modules(path) if _is_forbidden(module)]
    assert violations == [], f"{filename} imports forbidden modules: {violations}"
