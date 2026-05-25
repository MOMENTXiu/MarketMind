"""Realtime association rule calculation ability."""

from dataclasses import dataclass
from typing import Any

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder


@dataclass(frozen=True)
class RealtimeRuleCalculation:
    rules: list[dict[str, Any]]
    rows_to_persist: list[dict[str, Any]]


def calculate_realtime_rules(
    dataset: pd.DataFrame,
    item_name: str,
    min_confidence: float = 0.1,
    top_n: int = 10,
) -> RealtimeRuleCalculation:
    """Calculate downstream rules for one item without writing persistence artifacts."""

    target_orders = dataset[dataset["子类别"] == item_name]["订单 ID"].unique()
    subset = dataset[dataset["订单 ID"].isin(target_orders)]
    if len(subset) < 5:
        return RealtimeRuleCalculation(rules=[], rows_to_persist=[])

    basket = subset.groupby("订单 ID")["子类别"].apply(list).tolist()
    encoder = TransactionEncoder()
    encoded = encoder.fit_transform(basket)
    transaction_frame = pd.DataFrame(encoded, columns=encoder.columns_)
    frequent_itemsets = apriori(transaction_frame, min_support=0.01, use_colnames=True)
    if frequent_itemsets.empty:
        return RealtimeRuleCalculation(rules=[], rows_to_persist=[])

    rules = _association_rules(
        frequent_itemsets,
        metric="confidence",
        min_threshold=min_confidence,
    )
    filtered_rules = rules[rules["antecedents"].apply(lambda value: item_name in value)]

    results: list[dict[str, Any]] = []
    rows_to_persist: list[dict[str, Any]] = []
    total_orders = len(dataset["订单 ID"].unique())
    support_scale = len(target_orders) / total_orders if total_orders else 0.0

    for _, rule in filtered_rules.sort_values("lift", ascending=False).head(top_n).iterrows():
        if len(rule["consequents"]) > 1:
            continue
        consequent = list(rule["consequents"])[0]
        rule_result = {
            "item": consequent,
            "confidence": float(rule["confidence"]),
            "lift": float(rule["lift"]),
            "support": float(rule["support"]) * support_scale,
        }
        results.append(rule_result)
        rows_to_persist.append(
            {
                "antecedents": rule["antecedents"],
                "consequents": rule["consequents"],
                "support": rule_result["support"],
                "confidence": rule_result["confidence"],
                "lift": rule_result["lift"],
            }
        )

    return RealtimeRuleCalculation(rules=results, rows_to_persist=rows_to_persist)


def _association_rules(
    frequent_itemsets: pd.DataFrame,
    metric: str,
    min_threshold: float,
) -> pd.DataFrame:
    try:
        return association_rules(
            frequent_itemsets,
            metric=metric,
            min_threshold=min_threshold,
            num_itemsets=len(frequent_itemsets),
        )
    except TypeError:
        return association_rules(
            frequent_itemsets,
            metric=metric,
            min_threshold=min_threshold,
        )
