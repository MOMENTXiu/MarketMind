"""Build Retail V2 customer-category repurchase cycle features."""

from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-9


def build_repurchase_cycle(clean_sales: pd.DataFrame) -> pd.DataFrame:
    """Compute repurchase cycle metrics for each customer and leaf category."""

    clean_sales = clean_sales.copy()
    clean_sales["sale_date"] = pd.to_datetime(clean_sales["sale_date"])
    positive_sales = clean_sales[clean_sales["is_return"] == 0]
    current_date = clean_sales["sale_date"].max()
    rows: list[tuple[object, object, int, float, int, float]] = []

    grouped_dates = positive_sales.groupby(["user_id", "cat_l3_code"])["sale_date"]
    for (user_id, category_code), dates in grouped_dates:
        normalized_dates = np.sort(dates.dt.normalize().unique())
        purchase_count = len(normalized_dates)
        last_date = pd.Timestamp(normalized_dates[-1])
        if purchase_count >= 2:
            gaps = np.diff(normalized_dates).astype("timedelta64[D]").astype(float)
            average_cycle = float(gaps.mean())
        else:
            average_cycle = np.nan

        days_since_last = int((current_date - last_date).days)
        urgency = (
            days_since_last / (average_cycle + EPS)
            if average_cycle and not np.isnan(average_cycle)
            else np.nan
        )
        rows.append(
            (
                user_id,
                category_code,
                purchase_count,
                average_cycle,
                days_since_last,
                urgency,
            )
        )

    return pd.DataFrame(
        rows,
        columns=["user_id", "cat_l3_code", "购买次数", "平均复购周期天", "距今天数", "复购紧迫度"],
    )


def aggregate_customer_repurchase_need(
    customer_profile: pd.DataFrame,
    repurchase_cycle: pd.DataFrame,
) -> pd.DataFrame:
    """Attach customer-level repurchase urgency aggregates to a customer profile."""

    profile = customer_profile.copy()
    urgency_mean = (
        repurchase_cycle.dropna(subset=["复购紧迫度"]).groupby("user_id")["复购紧迫度"].mean()
    )
    cycle_mean = (
        repurchase_cycle.dropna(subset=["平均复购周期天"])
        .groupby("user_id")["平均复购周期天"]
        .mean()
    )
    profile = profile.merge(urgency_mean.rename("复购紧迫度均值"), on="user_id", how="left")
    profile = profile.merge(cycle_mean.rename("平均复购周期"), on="user_id", how="left")
    profile["复购紧迫度均值"] = profile["复购紧迫度均值"].fillna(0)
    fallback_cycle = profile["平均复购周期"].median()
    profile["平均复购周期"] = profile["平均复购周期"].fillna(
        0 if pd.isna(fallback_cycle) else fallback_cycle
    )
    return profile
