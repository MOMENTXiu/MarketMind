"""Repair Retail V2 rows shifted by commas inside specification text."""

from __future__ import annotations

import pandas as pd


def repair_shifted_sales_rows(raw_sales: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Repair rows whose promotion column no longer contains a yes/no flag."""

    repaired = raw_sales.copy()
    shifted = ~repaired["是否促销"].isin(["是", "否"])
    count = int(shifted.sum())
    if count == 0:
        return repaired, 0

    for index in repaired.index[shifted]:
        amount = pd.to_numeric(repaired.at[index, "商品单价"], errors="coerce")
        unit_price = pd.to_numeric(repaired.at[index, "是否促销"], errors="coerce")
        quantity = 1.0
        if pd.notna(amount) and pd.notna(unit_price) and unit_price != 0:
            quantity = round(float(amount) / float(unit_price), 4)

        spec_parts = [repaired.at[index, "规格型号"], repaired.at[index, "商品类型"]]
        repaired.at[index, "规格型号"] = " ".join(
            str(part).strip() for part in spec_parts if pd.notna(part) and str(part).strip()
        )
        repaired.at[index, "商品类型"] = "一般商品"
        repaired.at[index, "单位"] = "未知单位"
        repaired.at[index, "销售数量"] = quantity
        repaired.at[index, "销售金额"] = amount
        repaired.at[index, "商品单价"] = unit_price
        repaired.at[index, "是否促销"] = "否"

    return repaired, count
