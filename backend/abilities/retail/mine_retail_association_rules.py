"""Mine Retail V2 association rules using FP-Growth at item, L3, and L2 levels."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np  # noqa: F401
import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

from backend.core.errors import ValidationError

REQUIRED_COLUMNS = [
    "user_id",
    "sale_date",
    "item_id",
    "cat_l3_name",
    "cat_l2_name",
    "cat_l3_code",
    "amount",
    "is_return",
]


@dataclass(frozen=True)
class RetailAssociationRulesResult:
    """Output container for mine_retail_association_rules."""

    item_rules: pd.DataFrame
    category_l3_rules: pd.DataFrame
    category_l2_rules: pd.DataFrame
    category_rules: pd.DataFrame
    comparison_summary: pd.DataFrame


def _build_baskets(pos: pd.DataFrame, key: str) -> list[list]:
    g = pos.groupby(["user_id", "sale_date"])[key].apply(lambda s: sorted(set(s)))
    return [t for t in g.tolist() if len(t) >= 1]


def _mine_rules(
    transactions: list[list],
    min_support: float,
    min_confidence: float,
    min_lift: float,
    max_len: int = 3,
) -> tuple[pd.DataFrame, int]:
    te = TransactionEncoder()
    arr = te.fit_transform(transactions)
    dfb = pd.DataFrame(arr, columns=te.columns_)
    freq = fpgrowth(dfb, min_support=min_support, use_colnames=True, max_len=max_len)
    if freq.empty:
        return pd.DataFrame(), 0
    rules = association_rules(freq, metric="confidence", min_threshold=min_confidence)
    rules = rules[(rules["lift"] >= min_lift) & (rules["consequents"].apply(len) == 1)]
    rules = rules.sort_values(["lift", "confidence"], ascending=False)
    return rules, len(freq)


def _rules_to_cn(rules: pd.DataFrame, level: str) -> pd.DataFrame:
    if rules.empty:
        return pd.DataFrame()
    out = pd.DataFrame(
        {
            "层级": level,
            "前项": rules["antecedents"].apply(lambda s: "+".join(sorted(s))),
            "后项": rules["consequents"].apply(lambda s: list(s)[0]),
            "支持度": rules["support"].round(4),
            "置信度": rules["confidence"].round(4),
            "提升度": rules["lift"].round(3),
        }
    )
    return out.reset_index(drop=True)


def mine_retail_association_rules(
    clean_df: pd.DataFrame,
    item_min_support: float = 0.003,
    item_min_confidence: float = 0.20,
    item_min_lift: float = 1.10,
    l3_min_support: float = 0.01,
    l3_min_confidence: float = 0.25,
    l3_min_lift: float = 1.15,
    l2_min_support: float = 0.015,
    l2_min_confidence: float = 0.25,
    l2_min_lift: float = 1.15,
) -> RetailAssociationRulesResult:
    """Mine FP-Growth association rules at item, L3 category, and L2 category levels."""
    missing = [c for c in REQUIRED_COLUMNS if c not in clean_df.columns]
    if missing:
        raise ValidationError(f"clean_df missing required columns: {missing}")

    pos = clean_df[clean_df["is_return"] == 0]

    # E1: item-level
    tx_item = _build_baskets(pos, "item_id")
    rules_item, _ = _mine_rules(tx_item, item_min_support, item_min_confidence, item_min_lift, max_len=2)
    item_cn = _rules_to_cn(rules_item, "商品级")
    if not item_cn.empty:
        id2name = pos.drop_duplicates("item_id").set_index("item_id")["cat_l3_name"].to_dict()
        item_cn["前项类目"] = item_cn["前项"].apply(
            lambda s: "+".join(id2name.get(x, x) for x in s.split("+"))
        )
        item_cn["后项类目"] = item_cn["后项"].map(id2name)

    # E2: L3 category-level
    tx_l3 = _build_baskets(pos, "cat_l3_name")
    rules_l3, _ = _mine_rules(tx_l3, l3_min_support, l3_min_confidence, l3_min_lift, max_len=3)
    l3_cn = _rules_to_cn(rules_l3, "小类级")

    # L2 category-level
    tx_l2 = _build_baskets(pos, "cat_l2_name")
    rules_l2, _ = _mine_rules(tx_l2, l2_min_support, l2_min_confidence, l2_min_lift, max_len=2)
    l2_cn = _rules_to_cn(rules_l2, "中类级")

    category_rules = pd.concat([l3_cn, l2_cn], ignore_index=True)

    # Comparison summary
    def _stats(df: pd.DataFrame, name: str) -> dict:
        return {
            "实验": name,
            "规则数": len(df),
            "平均置信度": round(df["置信度"].mean(), 4) if not df.empty else 0.0,
            "平均提升度": round(df["提升度"].mean(), 3) if not df.empty else 0.0,
        }

    comparison_summary = pd.DataFrame(
        [
            _stats(item_cn, "E1_商品级FP"),
            _stats(l3_cn, "E2_小类级FP"),
            _stats(l2_cn, "E3_中类级FP"),
            _stats(category_rules, "E4_类目合并"),
        ]
    )

    return RetailAssociationRulesResult(
        item_rules=item_cn,
        category_l3_rules=l3_cn,
        category_l2_rules=l2_cn,
        category_rules=category_rules,
        comparison_summary=comparison_summary,
    )
