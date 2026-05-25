"""Contract tests for Retail V2 feature engineering abilities."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from backend.abilities.retail.build_customer_profile import build_customer_profile
from backend.abilities.retail.build_price_rank import build_price_rank
from backend.abilities.retail.build_product_profile import build_product_profile
from backend.abilities.retail.build_repurchase_cycle import (
    aggregate_customer_repurchase_need,
    build_repurchase_cycle,
)
from backend.abilities.retail.clean_retail_sales import clean_retail_sales
from backend.abilities.retail.rank_by_critic_topsis import critic_weights, topsis

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "analysis_v2" / "retail_sales_raw_gbk.csv"


def make_clean_sales() -> pd.DataFrame:
    raw_sales = pd.read_csv(FIXTURE)
    clean_sales = clean_retail_sales(raw_sales).clean_sales
    repeat_purchase = clean_sales.loc[clean_sales["user_id"] == "0001"].iloc[0].copy()
    repeat_purchase["sale_date"] = pd.Timestamp("2025-01-10")
    repeat_purchase["sale_month"] = 202501
    repeat_purchase["quantity"] = 1
    repeat_purchase["amount"] = 11
    repeat_purchase["unit_price"] = 11
    repeat_purchase["weekday"] = repeat_purchase["sale_date"].weekday()
    repeat_purchase["is_weekend"] = 0
    repeat_purchase["week_of_year"] = int(repeat_purchase["sale_date"].isocalendar().week)

    second_customer_purchase = clean_sales.loc[clean_sales["user_id"] == "0004"].iloc[0].copy()
    second_customer_purchase["user_id"] = "0003"
    second_customer_purchase["sale_date"] = pd.Timestamp("2025-03-05")
    second_customer_purchase["sale_month"] = 202503
    second_customer_purchase["weekday"] = second_customer_purchase["sale_date"].weekday()
    second_customer_purchase["is_weekend"] = 0
    second_customer_purchase["week_of_year"] = int(
        second_customer_purchase["sale_date"].isocalendar().week
    )

    return pd.concat(
        [clean_sales, repeat_purchase.to_frame().T, second_customer_purchase.to_frame().T],
        ignore_index=True,
    )


def test_critic_topsis_returns_stable_weights_and_scores() -> None:
    matrix = np.array([[10, 3, 1], [20, 2, 3], [30, 5, 2]], dtype=float)

    weights, detail = critic_weights(matrix)
    scores, rank_detail = topsis(matrix, weights)

    assert np.isclose(weights.sum(), 1.0)
    assert set(detail) == {"std", "conflict", "information"}
    assert scores.shape == (3,)
    assert scores.max() <= 1.0
    assert scores.min() >= 0.0
    assert rank_detail["weights"].shape == (3,)


def test_build_retail_customer_and_product_profiles() -> None:
    clean_sales = make_clean_sales()
    price_rank = build_price_rank(clean_sales)

    customer_profile, promotion_weights = build_customer_profile(clean_sales, price_rank)
    product_profile, product_weights = build_product_profile(clean_sales, price_rank)

    assert {"item_id", "cat_l3_code", "price_rank", "price_band"}.issubset(price_rank.columns)
    assert np.isclose(promotion_weights.sum(), 1.0)
    assert np.isclose(product_weights.sum(), 1.0)

    customer = customer_profile.set_index("user_id").loc["0001"]
    assert customer["F_购买频次"] == 2
    assert customer["M_消费金额"] == 31
    assert customer["促销敏感度"] > 0
    assert customer["退货率"] == 0
    assert customer["小类购买数"] == 1

    assert "0002" not in customer_profile["user_id"].tolist()

    product = product_profile.set_index("item_id").loc["9001"]
    assert product["销售笔数"] == 2
    assert product["购买人数"] == 1
    assert product["复购率"] == 1
    assert product["综合热度"] >= 0
    assert product["热度排名"] >= 1


def test_build_repurchase_cycle_and_customer_need() -> None:
    clean_sales = make_clean_sales()
    customer_profile, _ = build_customer_profile(clean_sales)

    repurchase_cycle = build_repurchase_cycle(clean_sales)
    enriched_profile = aggregate_customer_repurchase_need(customer_profile, repurchase_cycle)

    cycle = repurchase_cycle[
        (repurchase_cycle["user_id"] == "0001") & (repurchase_cycle["cat_l3_code"] == "1001")
    ].iloc[0]
    assert cycle["购买次数"] == 2
    assert cycle["平均复购周期天"] == 9
    assert "复购紧迫度均值" in enriched_profile.columns
    assert "平均复购周期" in enriched_profile.columns
