"""Unit tests for prediction and clustering abilities."""

from __future__ import annotations

import pandas as pd

from backend.abilities.clustering.build_cluster_association_rules import (
    build_cluster_association_rules,
)
from backend.abilities.clustering.cluster_customers import cluster_customers
from backend.abilities.prediction.forecast_sales import forecast_sales


def make_sales_dataset(weeks: int = 10) -> pd.DataFrame:
    rows = []
    for index in range(weeks):
        date = pd.Timestamp("2026-01-01") + pd.Timedelta(weeks=index)
        rows.append(
            {
                "订单日期": date.strftime("%Y-%m-%d"),
                "订单 ID": f"O{index}",
                "客户 ID": f"C{index % 4}",
                "子类别": "Milk" if index % 2 == 0 else "Bread",
                "销售额": 100 + index * 10,
                "利润": 20 + index * 3,
                "数量": 1 + index % 3,
                "折扣": 0.1,
                "细分": "Consumer",
                "地区": "East",
            }
        )
    return pd.DataFrame(rows)


def make_clustering_dataset() -> pd.DataFrame:
    rows = []
    for customer_index in range(6):
        for order_index in range(3):
            rows.append(
                {
                    "订单日期": (
                        pd.Timestamp("2026-01-01")
                        + pd.Timedelta(days=customer_index * 5 + order_index)
                    ).strftime("%Y-%m-%d"),
                    "订单 ID": f"O{customer_index}-{order_index}",
                    "客户 ID": f"C{customer_index}",
                    "子类别": "Milk" if order_index % 2 == 0 else "Bread",
                    "销售额": 100 + customer_index * 50 + order_index * 5,
                    "利润": 20 + customer_index * 10,
                    "数量": 1 + order_index,
                    "折扣": 0.05 * (customer_index % 3),
                    "细分": "Consumer",
                    "地区": "East",
                }
            )
    return pd.DataFrame(rows)


def test_forecast_sales_returns_current_result_shape() -> None:
    result = forecast_sales(make_sales_dataset(), forecast_weeks=2)

    assert result["success"] is True
    assert result["message"] == "销售预测完成"
    data = result["data"]
    assert {"sales_r2", "profit_r2", "train_samples", "forecast_weeks"}.issubset(data)
    assert data["forecast_weeks"] == 2
    assert len(data["forecast_data"]) == 2
    assert {"week", "date", "sales", "profit", "profit_rate"}.issubset(data["forecast_data"][0])
    assert {"total_sales", "total_profit", "avg_profit_rate"}.issubset(data["forecast_summary"])


def test_forecast_sales_reports_failure_for_too_little_data() -> None:
    result = forecast_sales(make_sales_dataset(weeks=2), forecast_weeks=1)

    assert result["success"] is False
    assert result["message"].startswith("预测失败:")
    assert result["data"] == {}


def test_cluster_customers_returns_profiles_contribution_and_customer_rows() -> None:
    result = cluster_customers(make_clustering_dataset(), n_clusters=3)

    assert result["success"] is True
    data = result["data"]
    assert data["total_customers"] == 6
    assert data["n_clusters"] == 3
    assert data["cluster_profiles"]
    assert data["contribution"]
    assert data["cluster_customers"]
    assert data["customer_rows"]
    assert {"cluster_id", "cluster_name", "marketing_strategy"}.issubset(
        data["cluster_profiles"][0]
    )


def test_cluster_customers_reports_failure_for_too_little_data() -> None:
    result = cluster_customers(make_clustering_dataset().head(1), n_clusters=2)

    assert result["success"] is False
    assert result["message"].startswith("聚类分析失败:")
    assert result["data"] == {}


def test_build_cluster_association_rules_returns_current_cluster_rule_shape() -> None:
    dataset = make_clustering_dataset()
    cluster_result = cluster_customers(dataset, n_clusters=2)
    customer_data = pd.DataFrame(cluster_result["data"]["customer_rows"])

    rules = build_cluster_association_rules(
        customer_data,
        dataset,
        min_support=0.01,
        min_confidence=0.1,
    )

    assert rules
    first_cluster_rules = next(iter(rules.values()))
    assert {"antecedent_to_consequent", "consequent_to_antecedent"}.issubset(first_cluster_rules)
