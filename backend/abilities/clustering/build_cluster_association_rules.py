"""Cluster-level association rule ability."""

from typing import Any

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder


def build_cluster_association_rules(
    customer_data: pd.DataFrame,
    dataset: pd.DataFrame,
    min_support: float = 0.05,
    min_confidence: float = 0.2,
) -> dict[int, dict[str, list[dict[str, Any]]]]:
    """Build per-cluster association rules without filesystem side effects."""

    cluster_rules = {}
    for cluster_id in customer_data["客户分群"].unique():
        customer_ids = customer_data[customer_data["客户分群"] == cluster_id]["客户ID"].tolist()
        cluster_orders = dataset[dataset["客户 ID"].isin(customer_ids)]
        cluster_rules[int(cluster_id)] = _build_rules_for_orders(
            cluster_orders,
            min_support=min_support,
            min_confidence=min_confidence,
        )
    return cluster_rules


def _build_rules_for_orders(
    cluster_orders: pd.DataFrame,
    min_support: float,
    min_confidence: float,
) -> dict[str, list[dict[str, Any]]]:
    empty_result = {"antecedent_to_consequent": [], "consequent_to_antecedent": []}
    if len(cluster_orders) < 10:
        return empty_result

    basket_data = cluster_orders.groupby("订单 ID")["子类别"].apply(list).reset_index()
    basket_data = basket_data[basket_data["子类别"].apply(len) > 1]
    if len(basket_data) < 5:
        return empty_result

    encoder = TransactionEncoder()
    encoded = encoder.fit_transform(basket_data["子类别"].tolist())
    basket_frame = pd.DataFrame(encoded, columns=encoder.columns_)
    frequent_itemsets = apriori(basket_frame, min_support=min_support, use_colnames=True)
    if frequent_itemsets.empty:
        return empty_result

    rules = _association_rules(frequent_itemsets, min_confidence)
    forward = []
    backward = []
    for _, rule in rules.sort_values("confidence", ascending=False).head(5).iterrows():
        antecedents = list(rule["antecedents"])
        consequents = list(rule["consequents"])
        base = {
            "confidence": round(float(rule["confidence"]), 4),
            "support": round(float(rule["support"]), 4),
            "lift": round(float(rule["lift"]), 2),
        }
        forward.append({"antecedent": antecedents, "consequent": consequents, **base})
        backward.append({"antecedent": consequents, "consequent": antecedents, **base})
    return {"antecedent_to_consequent": forward, "consequent_to_antecedent": backward}


def _association_rules(frequent_itemsets: pd.DataFrame, min_confidence: float) -> pd.DataFrame:
    try:
        return association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence,
            num_itemsets=len(frequent_itemsets),
        )
    except TypeError:
        return association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence,
        )
