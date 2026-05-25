"""Contract tests for Retail V2 recommendation ability atoms."""

from __future__ import annotations

import pandas as pd

from backend.abilities.retail.build_retail_recommendation_signals import (
    build_retail_recommendation_signals,
)
from backend.abilities.retail.rank_retail_recommendations import (
    rank_retail_recommendations,
)


def make_train_df() -> pd.DataFrame:
    """Minimal synthetic sales for recommendation testing (no file IO)."""
    items = [
        ("A001", "蔬果", "M001", "蔬菜", "L001"),
        ("A002", "蔬果", "M001", "水果", "L002"),
        ("B001", "粮油", "M002", "食用油", "L003"),
        ("B002", "粮油", "M002", "米面", "L004"),
        ("C001", "休闲", "M003", "零食", "L005"),
        ("C002", "休闲", "M003", "饮料", "L006"),
    ]
    users = ["u001", "u002", "u003", "u004", "u005"]
    dates = pd.date_range("2025-01-01", "2025-03-15", freq="14D")
    rows = []
    for u_idx, u in enumerate(users):
        for item_idx, (iid, l1, l2c, l3, l3c) in enumerate(items):
            if (u_idx + item_idx) % 2 == 0:
                for dt in dates[::2]:
                    rows.append(
                        {
                            "user_id": u,
                            "item_id": iid,
                            "cat_l1_name": l1,
                            "cat_l1_code": f"X{l2c[1:]}",
                            "cat_l2_name": l3,
                            "cat_l2_code": l2c,
                            "cat_l3_name": l3,
                            "cat_l3_code": l3c,
                            "sale_date": dt,
                            "sale_month": dt.year * 100 + dt.month,
                            "quantity": float(item_idx + 1),
                            "amount": float((item_idx + 1) * 20),
                            "unit_price": float((item_idx + 1) * 10),
                            "is_promo": 1 if item_idx % 3 == 0 else 0,
                            "is_return": False,
                            "spec": "default",
                            "item_type": "商品",
                            "unit": "个",
                            "weekday": dt.weekday(),
                            "is_weekend": int(dt.weekday() >= 5),
                            "week_of_year": int(dt.isocalendar().week),
                        }
                    )
    return pd.DataFrame(rows)


def test_build_retail_recommendation_signals_returns_required_fields() -> None:
    df = make_train_df()
    result = build_retail_recommendation_signals(df)

    assert isinstance(result.popularity, pd.Series)
    assert isinstance(result.item_meta, pd.DataFrame)
    assert isinstance(result.user_items, dict)
    assert isinstance(result.item_scoring_rules, dict)
    assert isinstance(result.l3_scoring_rules, dict)
    assert result.d_max is not pd.NaT
    assert len(result.popularity) > 0
    assert len(result.user_items) == 5  # 5 users


def test_rank_retail_recommendations_returns_top_k_per_user() -> None:
    signals = build_retail_recommendation_signals(make_train_df())
    recs = rank_retail_recommendations(signals, ["u001", "u002"], top_k=5)

    assert isinstance(recs, pd.DataFrame)
    assert set(recs.columns) >= {
        "user_id",
        "rank",
        "item_id",
        "cat_l3",
        "score",
        "主要来源",
        "reason",
    }
    for u in ["u001", "u002"]:
        user_recs = recs[recs["user_id"] == u]
        assert len(user_recs) <= 5
        assert (user_recs["rank"].values == list(range(1, len(user_recs) + 1))).all()


def test_rank_retail_recommendations_handles_cold_start_user() -> None:
    signals = build_retail_recommendation_signals(make_train_df())
    recs = rank_retail_recommendations(signals, ["new_user_99"], top_k=5)

    assert len(recs) > 0  # cold start: falls back to global popular items
    assert (recs["user_id"] == "new_user_99").all()
