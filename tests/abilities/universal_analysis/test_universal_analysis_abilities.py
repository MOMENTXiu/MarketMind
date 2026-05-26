"""Golden tests for universal analysis ability atoms."""

from __future__ import annotations

import pandas as pd

from backend.abilities.universal_analysis.build_overview import build_overview
from backend.abilities.universal_analysis.build_profile_segments import build_profile_segments
from backend.abilities.universal_analysis.build_universal_summary import build_universal_summary
from backend.abilities.universal_analysis.estimate_universal_promotion_effect import (
    estimate_universal_promotion_effect,
)
from backend.abilities.universal_analysis.mine_universal_associations import (
    mine_universal_associations,
)
from backend.abilities.universal_analysis.rank_universal_recommendations import (
    rank_universal_recommendations,
)


def _full_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": ["U001", "U001", "U002", "U002", "U003"],
            "item_id": ["SKU001", "SKU002", "SKU001", "SKU003", "SKU002"],
            "order_id": ["O001", "O001", "O002", "O002", "O003"],
            "sale_date": pd.to_datetime(
                ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"]
            ),
            "cat_l1_name": ["食品", "食品", "食品", "日用品", "食品"],
            "cat_l3_name": ["茶饮", "零食", "茶饮", "纸品", "零食"],
            "amount": [20.0, 15.0, 20.0, 10.0, 15.0],
            "quantity": [2, 1, 2, 1, 1],
            "unit_price": [10.0, 15.0, 10.0, 10.0, 15.0],
            "is_promo": [1, 0, 1, 0, 0],
            "discount": [0.0, 0.0, 0.1, 0.0, 0.0],
            "profit": [5.0, 3.0, 4.0, 2.0, 3.0],
        }
    )


def _sparse_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": ["U001", "U002", "U003"],
            "item_id": ["SKU001", "SKU001", "SKU001"],
            "order_id": ["O001", "O002", "O003"],
            "sale_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "amount": [10.0, 10.0, 10.0],
        }
    )


class TestBuildOverview:
    def test_overview_on_full_data(self) -> None:
        df = _full_df()
        cap: dict = {}
        result = build_overview(df, cap)
        assert "overview" in result
        assert result["overview"]["记录数"] == 5
        assert result["overview"]["总销售额"] == 80.0
        assert "category_sales" in result

    def test_skips_missing_fields_gracefully(self) -> None:
        df = pd.DataFrame({"amount": [10, 20]})
        result = build_overview(df, {})
        assert result["overview"]["记录数"] == 2


class TestBuildProfileSegments:
    def test_segments_on_full_data(self) -> None:
        df = pd.DataFrame(
            {
                "user_id": [f"U{i:03d}" for i in range(20)],
                "order_id": [f"O{i:03d}" for i in range(20)],
                "sale_date": pd.to_datetime(["2024-01-01"] * 20),
                "amount": [float(i * 10) for i in range(20)],
                "quantity": [i + 1 for i in range(20)],
                "cat_l1_name": ["食品"] * 10 + ["日用品"] * 10,
            }
        )
        cap: dict = {}
        result = build_profile_segments(df, cap)
        assert "n_segments" in result
        assert "silhouette" in result

    def test_skips_without_user_id(self) -> None:
        df = pd.DataFrame({"amount": [10, 20]})
        result = build_profile_segments(df, {})
        assert result["status"] == "skipped"


class TestMineUniversalAssociations:
    def test_skips_without_order_id(self) -> None:
        df = pd.DataFrame({"amount": [10, 20]})
        result = mine_universal_associations(df, {})
        assert result["status"] == "skipped"

    def test_skips_single_item_baskets(self) -> None:
        df = _sparse_df()
        result = mine_universal_associations(df, {})
        assert result["status"] == "skipped"

    def test_mines_rules_on_multi_item_baskets(self) -> None:
        df = _full_df()
        result = mine_universal_associations(df, {})
        assert result["status"] == "ok"
        assert result["n_rules"] >= 0
        assert result["avg_basket"] >= 1.5


class TestRankUniversalRecommendations:
    def test_skips_without_required_columns(self) -> None:
        df = pd.DataFrame({"amount": [10, 20]})
        result = rank_universal_recommendations(df, {})
        assert result["status"] == "skipped"

    def test_skips_sparse_repeat_users(self) -> None:
        df = _sparse_df()
        result = rank_universal_recommendations(df, {})
        assert result["status"] == "skipped"

    def test_recommends_on_sufficient_data(self) -> None:
        import numpy as np

        rng = np.random.default_rng(42)
        n = 200
        users = [f"U{i:03d}" for i in rng.integers(0, 30, n)]
        items = [f"SKU{i:03d}" for i in rng.integers(0, 50, n)]
        dates = pd.to_datetime([f"2024-01-{i % 28 + 1:02d}" for i in range(n)])
        df = pd.DataFrame(
            {
                "user_id": users,
                "item_id": items,
                "order_id": [f"O{i:04d}" for i in range(n)],
                "sale_date": dates,
                "amount": rng.uniform(10, 100, n).round(2),
                "cat_l1_name": rng.choice(["食品", "日用品", "饮料"], n),
            }
        )
        result = rank_universal_recommendations(df, {})
        assert result["status"] == "ok"
        assert "evaluation" in result
        assert "best_model" in result


class TestEstimateUniversalPromotionEffect:
    def test_skips_without_treatment(self) -> None:
        df = pd.DataFrame({"amount": [10, 20]})
        result = estimate_universal_promotion_effect(df, {})
        assert result["status"] == "skipped"

    def test_estimates_naive_diff(self) -> None:
        df = _full_df()
        result = estimate_universal_promotion_effect(df, {})
        assert result["status"] == "ok"
        assert "naive_diff" in result
        assert isinstance(result["naive_diff"], float)

    def test_discount_levels_when_present(self) -> None:
        df = _full_df()
        result = estimate_universal_promotion_effect(df, {})
        assert "discount_levels" in result


class TestBuildUniversalSummary:
    def test_aggregates_cross_module_results(self) -> None:
        summary = build_universal_summary(
            overview={"overview": {"总销售额": 100.0, "用户数": 3}},
            profile_segments={"n_segments": 2, "silhouette": 0.5},
            associations={"n_rules": 5, "top_rule": "A->B"},
            recommendations={"best_model": "热门", "fusion_hit": 0.12},
            promotion={"naive_diff": 5.0, "dml_ate": 4.5},
        )
        assert "基础销售统计" in summary
        assert "顾客画像" in summary
        assert "关联规则" in summary
        assert "个性化推荐" in summary
        assert "促销分析" in summary
        assert summary["基础销售统计"]["总销售额"] == 100.0
