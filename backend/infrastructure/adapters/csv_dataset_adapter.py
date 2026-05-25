"""CSV-backed dataset adapter."""

from pathlib import Path
from typing import Any

import pandas as pd


class CsvDatasetAdapter:
    """Load and save tabular datasets using the current local CSV layout."""

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir)
        self.projects_dir = self.data_dir / "projects"

    def load_dataset(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(path, encoding="utf-8")

    def load_project_dataset(self, project_id: str) -> pd.DataFrame:
        return self.load_dataset(self.projects_dir / project_id / "dataset.csv")

    def save_dataset(self, path: Path, rows: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(rows, pd.DataFrame):
            rows.to_csv(path, index=False)
            return
        pd.DataFrame(rows).to_csv(path, index=False)
