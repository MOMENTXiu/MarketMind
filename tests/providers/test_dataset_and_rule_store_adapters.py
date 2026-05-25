"""Contract tests for dataset and association rule store adapters."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.infrastructure.adapters.csv_dataset_adapter import CsvDatasetAdapter
from backend.infrastructure.adapters.local_association_rule_store_adapter import (
    LocalAssociationRuleStoreAdapter,
)


def test_csv_dataset_adapter_loads_and_saves_project_datasets(tmp_path: Path) -> None:
    adapter = CsvDatasetAdapter(str(tmp_path / "data"))
    dataset_path = tmp_path / "data/projects/project-1/dataset.csv"

    adapter.save_dataset(dataset_path, [{"订单 ID": "O1", "子类别": "Milk"}])

    loaded = adapter.load_dataset(dataset_path)
    project_loaded = adapter.load_project_dataset("project-1")
    assert loaded.to_dict(orient="records") == [{"订单 ID": "O1", "子类别": "Milk"}]
    assert project_loaded.equals(loaded)


def test_local_association_rule_store_loads_default_and_explicit_artifacts(
    tmp_path: Path,
) -> None:
    csv_rules = tmp_path / "association_rules.csv"
    pkl_rules = tmp_path / "association_rules.pkl"
    explicit_rules = tmp_path / "explicit_rules.csv"
    csv_frame = pd.DataFrame([{"antecedents": "Milk", "consequents": "Bread"}])
    pkl_frame = pd.DataFrame([{"antecedents": "Tea", "consequents": "Sugar"}])
    explicit_frame = pd.DataFrame([{"antecedents": "Coffee", "consequents": "Cake"}])
    csv_frame.to_csv(csv_rules, index=False)
    pkl_frame.to_pickle(pkl_rules)
    explicit_frame.to_csv(explicit_rules, index=False)

    adapter = LocalAssociationRuleStoreAdapter(rules_paths=[pkl_rules, csv_rules])

    assert adapter.load_rules().to_dict(orient="records") == [
        {"antecedents": "Tea", "consequents": "Sugar"}
    ]
    assert adapter.load_rules(dataset_path=explicit_rules).to_dict(orient="records") == [
        {"antecedents": "Coffee", "consequents": "Cake"}
    ]


def test_local_association_rule_store_saves_and_appends_dynamic_rules(
    tmp_path: Path,
) -> None:
    dynamic_rules_path = tmp_path / "backend/data/dynamic_rules.csv"
    adapter = LocalAssociationRuleStoreAdapter(
        rules_paths=[],
        dynamic_rules_path=str(dynamic_rules_path),
    )

    assert adapter.load_rules().empty
    assert list(adapter.load_rules().columns) == LocalAssociationRuleStoreAdapter.RULE_COLUMNS

    adapter.append_dynamic_rules([{"antecedents": "Milk", "consequents": "Bread"}])
    adapter.append_dynamic_rules([{"antecedents": "Tea", "consequents": "Sugar"}])
    dynamic_rows = pd.read_csv(dynamic_rules_path).to_dict(orient="records")
    assert dynamic_rows == [
        {"antecedents": "Milk", "consequents": "Bread"},
        {"antecedents": "Tea", "consequents": "Sugar"},
    ]

    saved_csv = tmp_path / "rules/saved.csv"
    adapter.save_rules(saved_csv, [{"antecedents": "Coffee", "consequents": "Cake"}])
    assert pd.read_csv(saved_csv).to_dict(orient="records") == [
        {"antecedents": "Coffee", "consequents": "Cake"}
    ]
