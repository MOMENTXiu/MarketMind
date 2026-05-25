"""Association rule artifact provider interface."""

from pathlib import Path
from typing import Any, Protocol


class AssociationRuleStoreProvider(Protocol):
    def load_rules(self, project_id: str | None = None, dataset_path: Path | None = None) -> Any:
        """Load association rules using current fallback semantics."""

    def append_dynamic_rules(self, rows: list[dict[str, Any]]) -> None:
        """Append realtime association rules."""

    def save_rules(self, path: Path, rows: Any) -> None:
        """Persist rule artifacts."""
