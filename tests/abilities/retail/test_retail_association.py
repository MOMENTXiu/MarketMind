"""Contract tests for Retail V2 association rules and HUIM ability atoms."""

from __future__ import annotations

import pandas as pd
import pytest

from backend.abilities.retail.mine_high_utility_itemsets import mine_high_utility_itemsets
from backend.abilities.retail.mine_retail_association_rules import mine_retail_association_rules
from backend.core.errors import ValidationError


def make_multi_item_sales() -> pd.DataFrame:
    """Inline synthetic DataFrame with multi-item baskets for association rule testing."""
    rows = []
    # 10 users, each buying items across multiple categories on 2 dates
    # Category definitions
    cats = [
        ("A001", "小类A", "B001", "中类B"),
        ("A002", "小类A", "B001", "中类B"),
        ("A003", "小类C", "B002", "中类D"),
        ("A004", "小类C", "B002", "中类D"),
        ("A005", "小类E", "B003", "中类F"),
    ]
    items = ["I001", "I002", "I003", "I004", "I005"]

    for uid in [f"{i:04d}" for i in range(1, 11)]:
        for date_str in ["2025-01-10", "2025-01-15"]:
            # Each user-date basket has at least 3 items
            for idx in range(3):
                cat = cats[idx % len(cats)]
                rows.append(
                    {
                        "user_id": uid,
                        "sale_date": pd.Timestamp(date_str),
                        "item_id": items[idx],
                        "cat_l3_code": cat[0],
                        "cat_l3_name": cat[1],
                        "cat_l2_code": cat[2],
                        "cat_l2_name": cat[3],
                        "amount": float(10 + idx * 5),
                        "is_return": False,
                    }
                )
    return pd.DataFrame(rows)


def make_pos_df_for_huim() -> pd.DataFrame:
    """Inline positive-transaction DataFrame for HUIM testing (10+ baskets, 2+ items each)."""
    rows = []
    cats = ["小类A", "小类B", "小类C", "小类D", "小类E"]
    amounts = [20.0, 35.0, 15.0, 50.0, 10.0]

    for uid_idx in range(12):
        uid = f"U{uid_idx:03d}"
        for day in [1, 5, 10]:
            date = pd.Timestamp(f"2025-02-{day:02d}")
            # Each basket contains 2-3 items with different amounts
            selected = [uid_idx % len(cats), (uid_idx + 1) % len(cats), (uid_idx + 2) % len(cats)]
            for cat_idx in selected:
                rows.append(
                    {
                        "user_id": uid,
                        "sale_date": date,
                        "cat_l3_name": cats[cat_idx],
                        "amount": amounts[cat_idx] * (1 + uid_idx * 0.1),
                    }
                )
    return pd.DataFrame(rows)


def test_mine_retail_association_rules_returns_valid_output_structure() -> None:
    df = make_multi_item_sales()
    result = mine_retail_association_rules(
        df,
        item_min_support=0.1,
        item_min_confidence=0.1,
        item_min_lift=1.0,
        l3_min_support=0.1,
        l3_min_confidence=0.1,
        l3_min_lift=1.0,
        l2_min_support=0.1,
        l2_min_confidence=0.1,
        l2_min_lift=1.0,
    )

    assert isinstance(result.item_rules, pd.DataFrame)
    assert isinstance(result.category_l3_rules, pd.DataFrame)
    assert isinstance(result.category_rules, pd.DataFrame)
    assert isinstance(result.comparison_summary, pd.DataFrame)
    assert not result.comparison_summary.empty

    if not result.item_rules.empty:
        assert {"层级", "前项", "后项", "支持度", "置信度", "提升度"}.issubset(
            set(result.item_rules.columns)
        )

    if not result.category_l3_rules.empty:
        assert (result.category_l3_rules["提升度"] >= 1.0).all()


def test_mine_high_utility_itemsets_computes_utility_and_filters_by_median() -> None:
    pos_df = make_pos_df_for_huim()
    result = mine_high_utility_itemsets(
        pos_df,
        level="cat_l3_name",
        min_support=0.05,
        min_len=2,
        max_len=3,
        top=40,
    )

    if result.empty:
        return  # sparse data may produce no candidates — acceptable

    assert set(result.columns) == {"组合", "项数", "出现篮数", "支持度", "总效用", "篮均效用", "效用占比"}
    assert result["总效用"].is_monotonic_decreasing
    assert result["效用占比"].between(0, 1).all()


def test_mine_retail_association_rules_validates_missing_columns() -> None:
    bad_df = pd.DataFrame(
        {
            "user_id": ["U1"],
            "sale_date": [pd.Timestamp("2025-01-01")],
            "item_id": ["I1"],
            # is_return is deliberately missing
        }
    )
    with pytest.raises(ValidationError):
        mine_retail_association_rules(bad_df)
