"""Mine high-utility itemsets (HUIM) from Retail V2 basket data."""

from __future__ import annotations

import pandas as pd
from mlxtend.frequent_patterns import fpgrowth
from mlxtend.preprocessing import TransactionEncoder

from backend.core.errors import ValidationError

_OUTPUT_COLUMNS = ["组合", "项数", "出现篮数", "支持度", "总效用", "篮均效用", "效用占比"]


def mine_high_utility_itemsets(
    pos_df: pd.DataFrame,
    level: str = "cat_l3_name",
    min_support: float = 0.002,
    min_len: int = 2,
    max_len: int = 3,
    top: int = 40,
) -> pd.DataFrame:
    """Mine high-utility itemsets from positive-transaction basket data.

    Returns a DataFrame with columns: 组合, 项数, 出现篮数, 支持度, 总效用, 篮均效用, 效用占比.
    Returns an empty DataFrame (with correct columns) when no candidates qualify.
    """
    required = ["user_id", "sale_date", "amount", level]
    missing = [c for c in required if c not in pos_df.columns]
    if missing:
        raise ValidationError(f"pos_df missing required columns: {missing}")

    # Build baskets (only keep multi-item transactions)
    basket_series = pos_df.groupby(["user_id", "sale_date"])[level].apply(lambda s: sorted(set(s)))
    baskets = [b for b in basket_series.tolist() if len(b) >= 2]
    n_tx = len(baskets)

    if n_tx == 0:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    # Candidate frequent itemsets via FP-Growth
    te = TransactionEncoder()
    arr = te.fit_transform(baskets)
    dfb = pd.DataFrame(arr, columns=te.columns_)
    freq = fpgrowth(dfb, min_support=min_support, use_colnames=True, max_len=max_len)
    freq = freq[freq["itemsets"].apply(len) >= min_len]

    if freq.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    # Build utility map: (user_id, sale_date, level_value) -> amount sum
    util_map = pos_df.groupby(["user_id", "sale_date", level])["amount"].sum().to_dict()

    # Reconstruct per-transaction utility dicts (only multi-item transactions)
    basket_keys_series = pos_df.groupby(["user_id", "sale_date"])[level].apply(set)
    tx_keys = [k for k, v in basket_keys_series.items() if len(v) >= 2]
    tx_sets = [basket_keys_series[k] for k in tx_keys]
    tx_util = []
    for k in tx_keys:
        u, d = k
        tx_util.append({c: util_map.get((u, d, c), 0.0) for c in basket_keys_series[k]})

    total_util = sum(sum(um.values()) for um in tx_util)

    rows = []
    for itemset in freq["itemsets"]:
        items = set(itemset)
        utility = 0.0
        cnt = 0
        for basket_set, um in zip(tx_sets, tx_util):
            if items.issubset(basket_set):
                utility += sum(um.get(i, 0.0) for i in items)
                cnt += 1
        if cnt == 0:
            continue
        rows.append(
            (
                "+".join(sorted(items)),
                len(items),
                cnt,
                round(cnt / n_tx, 4),
                round(utility, 2),
                round(utility / cnt, 2),
            )
        )

    if not rows:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    hui = pd.DataFrame(rows, columns=["组合", "项数", "出现篮数", "支持度", "总效用", "篮均效用"])

    # Filter by median utility, sort desc, take top
    threshold = hui["总效用"].quantile(0.5)
    hui = hui[hui["总效用"] >= threshold].sort_values("总效用", ascending=False).head(top)
    hui["效用占比"] = (hui["总效用"] / total_util).round(4)

    return hui[_OUTPUT_COLUMNS].reset_index(drop=True)
