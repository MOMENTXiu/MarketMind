"""CSV-backed dataset adapter."""

from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.errors import InfrastructureError


class CsvDatasetAdapter:
    """Load and save tabular datasets using the current local CSV layout."""

    DEFAULT_FALLBACKS: tuple[Path, ...] = (
        Path("data/dataset.csv"),
        Path("analysis/dataset.csv"),
        Path("dataset.csv"),
    )

    def __init__(
        self,
        data_dir: str = "data",
        default_fallbacks: tuple[Path, ...] | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.projects_dir = self.data_dir / "projects"
        self._default_fallbacks = default_fallbacks or self.DEFAULT_FALLBACKS

    def load_dataset(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(path, encoding="utf-8")

    def load_project_dataset(self, project_id: str) -> pd.DataFrame:
        return self.load_dataset(self.projects_dir / project_id / "dataset.csv")

    def resolve_default_path(self) -> Path | None:
        for candidate in self._default_fallbacks:
            if candidate.exists():
                return candidate
        return None

    def load_default(self) -> pd.DataFrame:
        path = self.resolve_default_path()
        if path is None:
            raise InfrastructureError(
                f"默认数据集不存在：请在 {self._default_fallbacks[0]} 或备选路径上传数据集"
            )
        return self.load_dataset(path)

    def save_dataset(self, path: Path, rows: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(rows, pd.DataFrame):
            rows.to_csv(path, index=False)
            return
        pd.DataFrame(rows).to_csv(path, index=False)
