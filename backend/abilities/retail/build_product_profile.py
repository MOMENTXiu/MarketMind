"""Build Retail V2 product profile features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.abilities.retail.build_price_rank import build_price_rank
from backend.abilities.retail.rank_by_critic_topsis import critic_weights, topsis


def build_product_profile(
    clean_sales: pd.DataFrame,
    price_rank: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Build product commercial profile and CRITIC-TOPSIS popularity rank."""

    clean_sales = clean_sales.copy()
    for column in ["amount", "quantity", "unit_price", "is_return", "is_promo"]:
        clean_sales[column] = pd.to_numeric(clean_sales[column])
    positive_sales = clean_sales[clean_sales["is_return"] == 0]
    if positive_sales.empty:
        return pd.DataFrame(columns=["item_id"]), np.array([])
    if price_rank is None:
        price_rank = build_price_rank(clean_sales)

    grouped = positive_sales.groupby("item_id")
    profile = pd.DataFrame(index=sorted(positive_sales["item_id"].unique()))
    profile.index.name = "item_id"
    metadata = positive_sales.groupby("item_id").agg(
        cat_l1_name=("cat_l1_name", "first"),
        cat_l2_name=("cat_l2_name", "first"),
        cat_l3_name=("cat_l3_name", "first"),
        cat_l3_code=("cat_l3_code", "first"),
        item_type=("item_type", "first"),
        unit=("unit", "first"),
        spec=("spec", "first"),
    )
    profile = profile.join(metadata)
    profile["销售金额"] = grouped["amount"].sum()
    profile["销售数量"] = grouped["quantity"].sum()
    profile["销售笔数"] = grouped.size()
    profile["平均单价"] = grouped["unit_price"].mean()
    profile["购买人数"] = grouped["user_id"].nunique()

    buyer_frequency = positive_sales.groupby(["item_id", "user_id"]).size()
    repeat_buyers = (buyer_frequency >= 2).groupby(level=0).sum().reindex(profile.index).fillna(0)
    profile["复购率"] = (repeat_buyers / profile["购买人数"]).fillna(0)
    global_repurchase_rate = repeat_buyers.sum() / profile["购买人数"].sum()
    prior_strength = 10.0
    profile["复购率_平滑"] = (repeat_buyers + global_repurchase_rate * prior_strength) / (
        profile["购买人数"] + prior_strength
    )
    profile["促销占比"] = grouped["is_promo"].mean()
    profile = profile.merge(price_rank, on=["item_id", "cat_l3_code"], how="left")

    metrics = profile[["销售金额", "销售数量", "购买人数"]].values
    compressed_metrics = np.log1p(np.clip(metrics, 0, None))
    ranking_matrix = np.column_stack([compressed_metrics, profile["复购率_平滑"].values])
    weights, _ = critic_weights(ranking_matrix)
    popularity, _ = topsis(ranking_matrix, weights)
    profile["综合热度"] = popularity
    profile["热度排名"] = profile["综合热度"].rank(ascending=False).astype(int)
    return profile.reset_index(), weights
