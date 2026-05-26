"""Build overview statistics: sales, categories, time trends, demographics, promotions."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.abilities.universal_analysis.common import positive


def build_overview(df: pd.DataFrame, _cap: dict[str, Any]) -> dict[str, Any]:
    """Return overview result dict with stats and figure payloads."""
    pos = positive(df)
    out: dict[str, Any] = {}

    def _has(c: str) -> bool:
        return c in df.columns

    ov = {
        "记录数": len(df),
        "用户数": df["user_id"].nunique() if _has("user_id") else None,
        "商品数": df["item_id"].nunique() if _has("item_id") else None,
        "订单数": df["order_id"].nunique() if _has("order_id") else None,
        "总销售额": round(pos["amount"].sum(), 2) if _has("amount") else None,
        "退货率": round(df["is_return"].mean(), 4) if _has("is_return") else None,
    }
    if _has("amount"):
        ov["客单价"] = round(
            pos["amount"].sum()
            / max(df["order_id"].nunique() if _has("order_id") else len(pos), 1),
            2,
        )
    out["overview"] = ov

    if _has("cat_l1_name") and _has("amount"):
        cs = pos.groupby("cat_l1_name")["amount"].sum().sort_values(ascending=False)
        out["top_category"] = cs.index[0]
        out["pareto_top20pct_share"] = round(cs.head(max(1, len(cs) // 5)).sum() / cs.sum(), 3)
        out["category_sales"] = cs.round(2).to_dict()

    if _has("sale_date") and _has("amount"):
        daily = pos.groupby(pos["sale_date"].dt.normalize())["amount"].sum()
        out["daily_sales"] = daily.round(2).to_dict()
        span = (daily.index.max() - daily.index.min()).days
        out["time_span_days"] = span

    if _has("is_promo") and _has("amount"):
        promo_total = pos[pos["is_promo"] == 1]["amount"].sum()
        total = pos["amount"].sum()
        out["promo_share"] = round(promo_total / total, 3) if total else 0.0

    return out
