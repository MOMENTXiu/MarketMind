"""Build Retail V2 customer profile features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.abilities.retail.build_price_rank import build_price_rank
from backend.abilities.retail.rank_by_critic_topsis import critic_weights

EPS = 1e-9
MAIN_CATEGORY_NAMES = ["蔬果", "休闲", "粮油", "日配", "洗化", "酒饮", "肉禽", "熟食"]


def build_customer_profile(
    clean_sales: pd.DataFrame,
    price_rank: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Build customer RFM, preference, promotion, price, and return features."""

    clean_sales = clean_sales.copy()
    clean_sales["sale_date"] = pd.to_datetime(clean_sales["sale_date"])
    for column in ["amount", "quantity", "unit_price", "is_return", "is_promo"]:
        clean_sales[column] = pd.to_numeric(clean_sales[column])
    positive_sales = clean_sales[clean_sales["is_return"] == 0].copy()
    if positive_sales.empty:
        return pd.DataFrame(columns=["user_id"]), np.array([0.5, 0.5])
    if price_rank is None:
        price_rank = build_price_rank(clean_sales)

    current_date = clean_sales["sale_date"].max()
    positive_sales = positive_sales.merge(
        price_rank[["item_id", "price_rank"]],
        on="item_id",
        how="left",
    )
    positive_sales["price_rank"] = positive_sales["price_rank"].fillna(0.5)

    grouped = positive_sales.groupby("user_id")
    profile = pd.DataFrame(index=sorted(positive_sales["user_id"].unique()))
    profile.index.name = "user_id"
    profile["R_最近购买间隔"] = (current_date - grouped["sale_date"].max()).dt.days
    profile["F_购买频次"] = grouped["sale_date"].nunique()
    profile["M_消费金额"] = grouped["amount"].sum()
    profile["记录数"] = grouped.size()
    profile["客单价"] = profile["M_消费金额"] / profile["F_购买频次"].clip(lower=1)
    profile["平均件单价"] = grouped["amount"].sum() / grouped["quantity"].sum().clip(lower=EPS)

    _attach_category_preferences(profile, positive_sales)
    _attach_fresh_share(profile, positive_sales)
    promotion_weights = _attach_promotion_sensitivity(profile, positive_sales)
    _attach_price_preference(profile, positive_sales)
    _attach_return_rate(profile, clean_sales)

    return profile.reset_index(), promotion_weights


def _attach_category_preferences(profile: pd.DataFrame, positive_sales: pd.DataFrame) -> None:
    category_amount = positive_sales.pivot_table(
        index="user_id",
        columns="cat_l1_name",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )
    category_share = category_amount.div(category_amount.sum(axis=1) + EPS, axis=0)
    for category_name in MAIN_CATEGORY_NAMES:
        profile[f"占比_{category_name}"] = (
            category_share[category_name] if category_name in category_share else 0.0
        )

    leaf_amount = positive_sales.pivot_table(
        index="user_id",
        columns="cat_l3_code",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )
    probabilities = leaf_amount.div(leaf_amount.sum(axis=1) + EPS, axis=0).values
    with np.errstate(divide="ignore", invalid="ignore"):
        entropy = -np.nansum(
            np.where(probabilities > 0, probabilities * np.log(probabilities), 0.0),
            axis=1,
        )
    profile["类目熵"] = pd.Series(entropy, index=leaf_amount.index)
    profile["小类购买数"] = (leaf_amount > 0).sum(axis=1)


def _attach_fresh_share(profile: pd.DataFrame, positive_sales: pd.DataFrame) -> None:
    fresh_amount = (
        positive_sales[positive_sales["item_type"] == "生鲜"].groupby("user_id")["amount"].sum()
    )
    profile["生鲜占比"] = (fresh_amount / profile["M_消费金额"]).fillna(0)


def _attach_promotion_sensitivity(
    profile: pd.DataFrame,
    positive_sales: pd.DataFrame,
) -> np.ndarray:
    promotion_sales = positive_sales[positive_sales["is_promo"] == 1]
    promotion_amount = promotion_sales.groupby("user_id")["amount"].sum()
    promotion_count = promotion_sales.groupby("user_id").size()
    profile["促销金额占比"] = (promotion_amount / profile["M_消费金额"]).fillna(0)
    profile["促销频次占比"] = (promotion_count / profile["记录数"]).fillna(0)
    promotion_matrix = profile[["促销金额占比", "促销频次占比"]].values
    weights, _ = critic_weights(promotion_matrix)
    profile["促销敏感度"] = promotion_matrix @ weights
    return weights


def _attach_price_preference(profile: pd.DataFrame, positive_sales: pd.DataFrame) -> None:
    low_amount = (
        positive_sales[positive_sales["price_rank"] <= 1 / 3].groupby("user_id")["amount"].sum()
    )
    high_amount = (
        positive_sales[positive_sales["price_rank"] >= 2 / 3].groupby("user_id")["amount"].sum()
    )
    profile["低价带占比"] = (low_amount / profile["M_消费金额"]).fillna(0)
    profile["高价带占比"] = (high_amount / profile["M_消费金额"]).fillna(0)

    positive_sales["_amount_price_rank"] = positive_sales["amount"] * positive_sales["price_rank"]
    preferred_rank = positive_sales.groupby("user_id")["_amount_price_rank"].sum() / (
        positive_sales.groupby("user_id")["amount"].sum() + EPS
    )
    profile["偏好价格分位"] = preferred_rank.fillna(0.5)


def _attach_return_rate(profile: pd.DataFrame, clean_sales: pd.DataFrame) -> None:
    return_count = clean_sales[clean_sales["is_return"] == 1].groupby("user_id").size()
    all_count = clean_sales.groupby("user_id").size()
    profile["退货率"] = (return_count / all_count).reindex(profile.index).fillna(0)
