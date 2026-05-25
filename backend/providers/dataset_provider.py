"""Dataset provider interface."""

from pathlib import Path
from typing import Any, Protocol


class DatasetProvider(Protocol):
    def load_dataset(self, path: Path) -> Any:
        """Load a tabular dataset without exposing storage details to abilities."""

    def load_project_dataset(self, project_id: str) -> Any:
        """Load the current dataset for a project."""

    def save_dataset(self, path: Path, rows: Any) -> None:
        """Save tabular data to a dataset path."""
