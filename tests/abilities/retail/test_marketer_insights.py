"""Contract tests for Retail V2 marketer and causal ability atoms."""

from __future__ import annotations

import pandas as pd
import pytest

from backend.abilities.retail.build_marketer_insights import build_marketer_insights
from backend.abilities.retail.estimate_customer_uplift import estimate_customer_uplift
from backend.abilities.retail.estimate_promotion_effect import estimate_promotion_effect
from backend.core.errors import ValidationError


def make_clean_sales() -> pd.DataFrame:
    rows = []
    users = [f"U{index:03d}" for index in range(16)]
    categories = [
        ("C01", "蔬果", "M01", "蔬菜", "L01", "I01", 10.0),
        ("C02", "粮油", "M02", "米面", "L02", "I02", 18.0),
    ]
    dates = pd.to_datetime(["2025-01-05", "2025-02-05", "2025-03-05", "2025-04-05"])

    for user_index, user_id in enumerate(users):
        high_value = user_index < 8
        for month_index, sale_date in enumerate(dates):
            cat_l1_code, cat_l1_name, cat_l2_code, cat_l3_name, cat_l3_code, item_id, price = (
                categories[(user_index + month_index) % len(categories)]
            )
            is_promo = int((user_index + month_index) % 2 == 0)
            base_amount = 46.0 if high_value else 22.0
            amount = base_amount + price + (9.0 if is_promo else 0.0)
            rows.append(
                {
                    "user_id": user_id,
                    "cat_l1_code": cat_l1_code,
                    "cat_l1_name": cat_l1_name,
                    "cat_l2_code": cat_l2_code,
                    "cat_l2_name": cat_l3_name,
                    "cat_l3_code": cat_l3_code,
                    "cat_l3_name": cat_l3_name,
                    "sale_date": sale_date,
                    "sale_month": sale_date.year * 100 + sale_date.month,
                    "item_id": item_id,
                    "spec": "standard",
                    "item_type": "商品",
                    "unit": "个",
                    "quantity": 1.0,
                    "amount": amount,
                    "unit_price": price,
                    "is_promo": is_promo,
                    "is_return": 0,
                    "weekday": sale_date.weekday(),
                    "is_weekend": int(sale_date.weekday() >= 5),
                    "week_of_year": int(sale_date.isocalendar().week),
                }
            )
    return pd.DataFrame(rows)


def make_customer_profile(clean_sales: pd.DataFrame) -> pd.DataFrame:
    grouped = clean_sales.groupby("user_id")
    profile = grouped.agg(
        M_消费金额=("amount", "sum"),
        F_购买频次=("sale_date", "nunique"),
        记录数=("item_id", "size"),
    ).reset_index()
    promotion_amount = clean_sales[clean_sales["is_promo"] == 1].groupby("user_id")["amount"].sum()
    promotion_count = clean_sales[clean_sales["is_promo"] == 1].groupby("user_id").size()
    profile["促销金额占比"] = (
        (promotion_amount / profile.set_index("user_id")["M_消费金额"]).fillna(0).values
    )
    profile["促销频次占比"] = (
        (promotion_count / profile.set_index("user_id")["记录数"]).fillna(0).values
    )
    profile["促销敏感度"] = profile["促销金额占比"] * 0.7 + profile["促销频次占比"] * 0.3
    profile["R_最近购买间隔"] = [4 + index if index < 8 else 28 + index for index in range(16)]
    return profile


def make_customer_segments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "user_id": f"U{index:03d}",
                "segment_id": 0 if index < 8 else 1,
                "segment": "高价值稳定型" if index < 8 else "促销敏感型",
                "segment_confidence": 0.9,
            }
            for index in range(16)
        ]
    )


def make_high_utility_itemsets() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "组合": "米面+蔬菜",
                "项数": 2,
                "出现篮数": 12,
                "支持度": 0.45,
                "总效用": 720.0,
                "篮均效用": 60.0,
                "效用占比": 0.30,
            }
        ]
    )


def make_association_rules() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "层级": "小类级",
                "前项": "蔬菜",
                "后项": "米面",
                "支持度": 0.35,
                "置信度": 0.66,
                "提升度": 1.40,
            }
        ]
    )


def test_estimate_promotion_effect_returns_overall_and_segment_rows() -> None:
    clean_sales = make_clean_sales()
    profile = make_customer_profile(clean_sales)
    segments = make_customer_segments()

    result = estimate_promotion_effect(clean_sales, profile, segments, min_group_size=8, n_folds=3)

    assert result.naive_ate > 0
    assert result.overall_effect["n"] == len(clean_sales)
    assert result.overall_effect["method"] in {"dml_cross_fit", "naive_fallback"}
    assert {"全体(ATE)", "高价值稳定型", "促销敏感型"}.issubset(set(result.effect_detail["群体"]))
    assert {"群体", "朴素PromoLift", "促销销售占比", "DML因果效应"}.issubset(
        result.promotion_response.columns
    )


def test_estimate_promotion_effect_falls_back_for_single_treatment_class() -> None:
    clean_sales = make_clean_sales()
    clean_sales["is_promo"] = 1
    profile = make_customer_profile(clean_sales)
    segments = make_customer_segments()

    result = estimate_promotion_effect(clean_sales, profile, segments, min_group_size=8, n_folds=3)

    assert result.naive_ate == 0.0
    assert str(result.overall_effect["method"]).startswith("naive_fallback")
    assert result.effect_detail.loc[0, "DML因果效应"] == 0.0


def test_estimate_customer_uplift_ranks_expected_columns_and_priorities() -> None:
    clean_sales = make_clean_sales()
    profile = make_customer_profile(clean_sales)
    segments = make_customer_segments()
    promotion_effect = estimate_promotion_effect(
        clean_sales, profile, segments, min_group_size=8, n_folds=3
    )

    result = estimate_customer_uplift(profile, segments, promotion_effect, top_k=5)

    assert len(result.customer_uplift) == 5
    assert {
        "user_id",
        "segment",
        "segment_effect",
        "expected_incremental_amount",
        "uplift_score",
        "uplift_rank",
        "target_priority",
    }.issubset(result.customer_uplift.columns)
    assert result.customer_uplift["uplift_rank"].tolist() == [1, 2, 3, 4, 5]
    assert result.customer_uplift.iloc[0]["target_priority"] == "高优先级"
    assert not result.segment_uplift.empty


def test_build_marketer_insights_returns_all_outputs_and_weights() -> None:
    clean_sales = make_clean_sales()
    profile = make_customer_profile(clean_sales)
    segments = make_customer_segments()

    insights = build_marketer_insights(
        clean_sales,
        profile,
        segments,
        high_utility_itemsets=make_high_utility_itemsets(),
        association_rules=make_association_rules(),
        top_bundles=5,
    )

    assert not insights.segment_value.empty
    assert not insights.bundle_strategy.empty
    assert not insights.promotion_response.empty
    assert not insights.promotion_effect_detail.empty
    assert not insights.customer_uplift.empty
    assert not insights.segment_uplift.empty
    assert not insights.category_strategy.empty
    assert set(insights.weights) == {"segment_value", "bundle_strategy"}
    assert "营销价值得分" in insights.segment_value.columns
    assert "经营策略" in insights.category_strategy.columns


def test_marketer_abilities_validate_missing_required_columns() -> None:
    clean_sales = make_clean_sales()
    profile = make_customer_profile(clean_sales)
    segments = make_customer_segments()

    with pytest.raises(ValidationError, match="amount"):
        estimate_promotion_effect(clean_sales.drop(columns=["amount"]), profile, segments)

    with pytest.raises(ValidationError, match="促销敏感度"):
        estimate_customer_uplift(profile.drop(columns=["促销敏感度"]), segments, None)  # type: ignore[arg-type]
