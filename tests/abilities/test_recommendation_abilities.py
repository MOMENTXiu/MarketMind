"""Unit tests for recommendation abilities."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.abilities.recommendation.build_recommendation_model import (
    build_recommendation_model,
)
from backend.abilities.recommendation.recommend_for_item import recommend_for_item
from backend.abilities.recommendation.recommend_for_user import recommend_for_user


@dataclass
class AssociationRuleFixture:
    antecedents: list[str]
    consequent: str
    support: float
    confidence: float
    lift: float


def make_recommendation_dataset() -> pd.DataFrame:
    rows = []
    items = ["Milk", "Bread", "Desk", "Chair"]
    categories = {"Milk": "Food", "Bread": "Food", "Desk": "Office", "Chair": "Office"}
    for customer_index in range(6):
        for order_index in range(3):
            for item_offset in range(2):
                item = items[(customer_index + order_index + item_offset) % len(items)]
                rows.append(
                    {
                        "订单日期": (
                            pd.Timestamp("2026-01-01")
                            + pd.Timedelta(days=customer_index * 5 + order_index)
                        ).strftime("%Y-%m-%d"),
                        "订单 ID": f"O{customer_index}-{order_index}",
                        "客户 ID": f"C{customer_index}",
                        "类别": categories[item],
                        "子类别": item,
                        "销售额": 100 + customer_index * 50 + order_index * 10 + item_offset,
                        "利润": 20 + customer_index * 8 + item_offset,
                        "数量": 1 + item_offset,
                        "折扣": 0.05 * (customer_index % 3),
                        "细分": "Consumer",
                        "地区": "East",
                    }
                )
    return pd.DataFrame(rows)


def make_rules() -> list[AssociationRuleFixture]:
    return [
        AssociationRuleFixture(
            antecedents=["Milk"],
            consequent="Bread",
            support=0.4,
            confidence=0.8,
            lift=1.6,
        ),
        AssociationRuleFixture(
            antecedents=["Desk"],
            consequent="Milk",
            support=0.3,
            confidence=0.6,
            lift=1.2,
        ),
    ]


def test_build_recommendation_model_returns_model_data_without_persistence() -> None:
    result = build_recommendation_model(
        make_recommendation_dataset(),
        association_rules=make_rules(),
        n_clusters=3,
    )

    assert result["success"] is True
    assert result["total_customers"] == 6
    assert result["n_clusters"] == 3
    assert result["n_rules"] == 2
    model_data = result["model_data"]
    assert {"kmeans_model", "cluster_scaler", "customer_data", "rules_single"}.issubset(model_data)
    assert not model_data["rules_single"].empty


def test_build_recommendation_model_reports_failure_for_too_little_data() -> None:
    result = build_recommendation_model(make_recommendation_dataset().head(1), n_clusters=2)

    assert result["success"] is False
    assert result["model_data"] == {}
    assert "数据量过少" in result["error"]


def test_recommend_for_user_uses_model_data_current_shape() -> None:
    dataset = make_recommendation_dataset()
    model_data = build_recommendation_model(dataset, association_rules=make_rules(), n_clusters=2)[
        "model_data"
    ]

    result = recommend_for_user(dataset, model_data, user_id="C1", top_n=2)

    assert result["recommends"]
    assert len(result["recommends"]) == 2
    assert {"item", "category", "score", "avg_price", "reason"}.issubset(result["recommends"][0])
    assert {"cluster_id", "cluster_name", "strategy"}.issubset(result["cluster"])


def test_recommend_for_user_falls_back_without_model_data() -> None:
    result = recommend_for_user(
        make_recommendation_dataset(), model_data=None, user_id="C1", top_n=2
    )

    assert len(result["recommends"]) == 2
    assert result["cluster"] == {
        "cluster_id": -1,
        "cluster_name": "未分类",
        "strategy": "基于热门商品推荐（模型未加载）",
    }


def test_recommend_for_item_returns_bidirectional_rules_and_targets() -> None:
    dataset = make_recommendation_dataset()
    model_data = build_recommendation_model(dataset, association_rules=make_rules(), n_clusters=2)[
        "model_data"
    ]

    result = recommend_for_item(model_data, "Milk", dataset=dataset)

    assert result["item"] == "Milk"
    assert result["downstream"] == [
        {"item": "Bread", "confidence": 0.8, "lift": 1.6, "support": 0.4}
    ]
    assert result["upstream"] == [{"item": "Desk", "confidence": 0.6, "lift": 1.2, "support": 0.3}]
    assert result["target_customers"]
    assert {"cluster_name", "buyer_count", "lift_index", "strategy"}.issubset(
        result["target_customers"][0]
    )
