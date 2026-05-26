"""Architecture boundary checks for staged backend migration."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

FORBIDDEN_DIRECT_IMPORT_PREFIXES = {
    "api": (
        "edge_tts",
        "httpx",
        "pandas",
        "sklearn",
        "mlxtend",
        "backend.infrastructure",
    ),
    "business": (
        "edge_tts",
        "httpx",
        "pandas",
        "sklearn",
        "mlxtend",
        "fastapi",
        "backend.api",
        "backend.infrastructure",
    ),
    "abilities": (
        "edge_tts",
        "httpx",
        "fastapi",
        "backend.api",
        "backend.business",
        "backend.infrastructure",
    ),
    "providers": (
        "edge_tts",
        "httpx",
        "pandas",
        "sklearn",
        "mlxtend",
        "fastapi",
        "backend.api",
        "backend.business",
        "backend.abilities",
        "backend.infrastructure",
        "backend.core.config",
    ),
}

LEGACY_IMPORT_ALLOWLIST = {
    ("api/dependencies.py", "backend.infrastructure.factories.provider_factory"),
}

GENERIC_FALLBACK_NAMES = {"helpers", "common", "misc"}


def iter_python_files() -> list[Path]:
    return [path for path in BACKEND.rglob("*.py") if ".venv" not in path.parts]


def layer_for(path: Path) -> str | None:
    rel = path.relative_to(BACKEND)
    return rel.parts[0] if rel.parts else None


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def is_forbidden(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)


def test_no_new_layer_import_violations() -> None:
    violations: list[str] = []
    for path in iter_python_files():
        layer = layer_for(path)
        prefixes = FORBIDDEN_DIRECT_IMPORT_PREFIXES.get(layer)
        if prefixes is None:
            continue

        rel = path.relative_to(BACKEND).as_posix()
        for module in imported_modules(path):
            if not is_forbidden(module, prefixes):
                continue
            if (rel, module) in LEGACY_IMPORT_ALLOWLIST:
                continue
            violations.append(f"{rel} imports forbidden module {module}")

    assert violations == []


def test_backend_runtime_does_not_import_analysis_code_files() -> None:
    violations: list[str] = []
    for path in iter_python_files():
        rel = path.relative_to(BACKEND).as_posix()
        for module in imported_modules(path):
            if module == "analysis.code_files" or module.startswith("analysis.code_files."):
                violations.append(f"{rel} imports forbidden runtime blueprint {module}")

    assert violations == []


def test_no_new_generic_fallback_modules() -> None:
    offenders = [
        path.relative_to(BACKEND).as_posix()
        for path in BACKEND.rglob("*")
        if path.is_dir() and path.name in GENERIC_FALLBACK_NAMES
    ]

    assert offenders == []


def test_existing_utils_package_stays_empty() -> None:
    utils_dir = BACKEND / "utils"
    if not utils_dir.exists():
        return

    files = [path.name for path in utils_dir.iterdir() if path.is_file()]
    assert files in ([], ["__init__.py"])
