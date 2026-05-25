"""Local association rule artifact store adapter."""

from pathlib import Path
from typing import Any

import pandas as pd


class LocalAssociationRuleStoreAdapter:
    """Load and save association rule artifacts using current local files."""

    RULE_COLUMNS = ["antecedents", "consequents", "support", "confidence", "lift", "strategy"]

    def __init__(
        self,
        rules_paths: list[Path] | None = None,
        dynamic_rules_path: str = "backend/data/dynamic_rules.csv",
    ) -> None:
        self.rules_paths = rules_paths or [
            Path("data/association_rules.pkl"),
            Path("data/association_rules.csv"),
        ]
        self.dynamic_rules_path = Path(dynamic_rules_path)

    def load_rules(
        self, project_id: str | None = None, dataset_path: Path | None = None
    ) -> pd.DataFrame:
        if dataset_path and dataset_path.exists() and dataset_path.suffix in {".pkl", ".csv"}:
            return self._load_rule_file(dataset_path)

        for path in self.rules_paths:
            if path.exists():
                return self._load_rule_file(path)

        return pd.DataFrame(columns=self.RULE_COLUMNS)

    def append_dynamic_rules(self, rows: list[dict[str, Any]]) -> None:
        self.dynamic_rules_path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(rows)
        frame.to_csv(
            self.dynamic_rules_path,
            mode="a",
            header=not self.dynamic_rules_path.exists(),
            index=False,
        )

    def save_rules(self, path: Path, rows: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        if path.suffix == ".pkl":
            frame.to_pickle(path)
            return
        frame.to_csv(path, index=False)

    @staticmethod
    def _load_rule_file(path: Path) -> pd.DataFrame:
        if path.suffix == ".pkl":
            return pd.read_pickle(path)
        return pd.read_csv(path)
