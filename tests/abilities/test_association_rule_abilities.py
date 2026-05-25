"""Unit tests for association rule abilities."""

from __future__ import annotations

import pandas as pd

from backend.abilities.association.analyze_association_rules import analyze_association_rules
from backend.abilities.association.calculate_realtime_rules import calculate_realtime_rules


def make_transactions() -> pd.DataFrame:
    rows = []
    baskets = [
        ("O1", ["Milk", "Bread"]),
        ("O2", ["Milk", "Bread"]),
        ("O3", ["Milk", "Bread", "Eggs"]),
        ("O4", ["Milk", "Eggs"]),
        ("O5", ["Milk", "Bread"]),
        ("O6", ["Tea", "Sugar"]),
    ]
    for order_id, items in baskets:
        for item in items:
            rows.append({"订单 ID": order_id, "子类别": item})
    return pd.DataFrame(rows)


def test_analyze_association_rules_returns_current_response_shape() -> None:
    result = analyze_association_rules(
        make_transactions(),
        min_support=0.2,
        min_confidence=0.5,
        min_lift=0.1,
        top_n=5,
    )

    assert result.success is True
    assert result.message == "关联规则分析完成"
    assert result.data["total_orders"] == 6
    assert result.data["frequent_itemsets"] > 0
    assert result.rules
    first_rule = result.rules[0]
    assert first_rule.antecedents
    assert first_rule.consequent
    assert first_rule.strategy.startswith("购买")


def test_analyze_association_rules_handles_no_multi_item_orders() -> None:
    result = analyze_association_rules(
        pd.DataFrame(
            [
                {"订单 ID": "O1", "子类别": "Milk"},
                {"订单 ID": "O2", "子类别": "Bread"},
            ]
        )
    )

    assert result.success is True
    assert result.data["total_orders"] == 0
    assert result.rules == []


def test_calculate_realtime_rules_returns_results_and_persistence_rows() -> None:
    result = calculate_realtime_rules(
        make_transactions(),
        item_name="Milk",
        min_confidence=0.5,
    )

    assert result.rules
    assert result.rows_to_persist
    assert result.rules[0]["item"]
    assert {"antecedents", "consequents", "support", "confidence", "lift"}.issubset(
        result.rows_to_persist[0]
    )


def test_calculate_realtime_rules_keeps_small_subset_fallback() -> None:
    result = calculate_realtime_rules(
        pd.DataFrame(
            [
                {"订单 ID": "O1", "子类别": "Milk"},
                {"订单 ID": "O1", "子类别": "Bread"},
            ]
        ),
        item_name="Milk",
    )

    assert result.rules == []
    assert result.rows_to_persist == []
