"""Build Retail V2 item price-rank features."""

from __future__ import annotations

import pandas as pd


def build_price_rank(clean_sales: pd.DataFrame) -> pd.DataFrame:
    """Compute item price percentile and price band inside each category."""

    clean_sales = clean_sales.copy()
    clean_sales["unit_price"] = pd.to_numeric(clean_sales["unit_price"])
    item_price = clean_sales.groupby(["cat_l3_code", "item_id"], as_index=False)[
        "unit_price"
    ].mean()
    item_price["price_rank"] = item_price.groupby("cat_l3_code")["unit_price"].rank(pct=True)
    item_price["price_band"] = pd.cut(
        item_price["price_rank"],
        [0, 1 / 3, 2 / 3, 1.0],
        labels=["低价带", "中价带", "高价带"],
        include_lowest=True,
    ).astype(str)
    return item_price[["item_id", "cat_l3_code", "price_rank", "price_band"]]
