"""Item recommendation ability."""

from typing import Any

import pandas as pd


def recommend_for_item(
    model_data: dict[str, Any] | None,
    item_name: str,
    top_n: int = 8,
    dataset: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Recommend upstream/downstream item relations from explicit model data."""

    if not model_data:
        return {"item": item_name, "upstream": [], "downstream": [], "target_customers": []}

    rules_single = model_data.get("rules_single", pd.DataFrame())
    upstream = _format_rule_direction(rules_single, item_name, direction="upstream", top_n=top_n)
    downstream = _format_rule_direction(
        rules_single, item_name, direction="downstream", top_n=top_n
    )
    targets = _target_customers(model_data, item_name, dataset)
    return {
        "item": item_name,
        "upstream": upstream,
        "downstream": downstream,
        "target_customers": targets,
    }


def _format_rule_direction(
    rules_single: pd.DataFrame,
    item_name: str,
    direction: str,
    top_n: int,
) -> list[dict[str, Any]]:
    if rules_single.empty or "antecedents" not in rules_single.columns:
        return []

    if direction == "downstream":
        frame = rules_single[
            rules_single["antecedents"].apply(lambda value: item_name in value)
        ].copy()
        item_column = "consequents"
    else:
        frame = rules_single[
            rules_single["consequents"].apply(lambda value: item_name in value)
        ].copy()
        item_column = "antecedents"

    if frame.empty:
        return []

    results = []
    for _, row in frame.sort_values("confidence", ascending=False).head(top_n).iterrows():
        items = list(row[item_column])
        results.append(
            {
                "item": items[0] if items else "",
                "confidence": float(row["confidence"]),
                "lift": float(row["lift"]),
                "support": float(row["support"]),
            }
        )
    return results


def _target_customers(
    model_data: dict[str, Any],
    item_name: str,
    dataset: pd.DataFrame | None,
) -> list[dict[str, Any]]:
    if item_name not in model_data.get("subcategories", []) or dataset is None:
        return []

    customer_data = model_data["customer_data"]
    cluster_profiles = model_data["cluster_profiles"]
    product_cluster_stats = _product_cluster_stats(model_data, dataset)
    cluster_stats = product_cluster_stats[product_cluster_stats["子类别"] == item_name].copy()
    if cluster_stats.empty:
        return []

    total_buyers = cluster_stats["购买客户数"].sum() or 1
    total_customers = len(customer_data) or 1
    cluster_sizes = cluster_profiles["客户数"].to_dict()
    cluster_stats["购买占比"] = cluster_stats["购买客户数"] / total_buyers * 100
    cluster_stats["群体占比"] = (
        cluster_stats["分群名称"].map(
            {cluster_profiles.loc[key, "群体名称"]: value for key, value in cluster_sizes.items()}
        )
        / total_customers
        * 100
    )
    cluster_stats["购买倾向指数"] = cluster_stats["购买占比"] / cluster_stats["群体占比"]
    strategy_map = cluster_profiles.set_index("群体名称")["营销策略"].to_dict()
    cluster_stats = cluster_stats.sort_values("购买倾向指数", ascending=False).head(5)
    return [
        {
            "cluster_name": row["分群名称"],
            "buyer_count": int(row["购买客户数"]),
            "lift_index": float(row["购买倾向指数"]),
            "strategy": strategy_map.get(row["分群名称"], "常规营销"),
        }
        for _, row in cluster_stats.iterrows()
    ]


def _product_cluster_stats(model_data: dict[str, Any], dataset: pd.DataFrame) -> pd.DataFrame:
    frame = dataset.copy()
    customer_cluster_map = model_data["customer_data"].set_index("客户ID")["客户分群"].to_dict()
    frame["客户分群"] = frame["客户 ID"].map(customer_cluster_map)
    cluster_name_map = model_data["cluster_profiles"]["群体名称"].to_dict()
    frame["分群名称"] = frame["客户分群"].map(cluster_name_map)
    stats = (
        frame.groupby(["子类别", "分群名称"])
        .agg({"客户 ID": "nunique", "销售额": "sum", "数量": "sum"})
        .reset_index()
    )
    stats.columns = ["子类别", "分群名称", "购买客户数", "销售额", "销量"]
    return stats
