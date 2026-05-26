"""Business normalization: pseudo order_id, amount/qty/price completion, unit normalization, return flagging."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.abilities.regularization.field_aliases import UNIT_ALIASES, UNIT_DIRTY

_UNIT_MAP: dict[str, str] = {}
for std, al in UNIT_ALIASES.items():
    for a in al:
        _UNIT_MAP[str(a).strip().lower()] = std


def normalize_business_fields(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return (normalized dataframe, applied rules list)."""
    df = df.copy()
    rules: list[str] = []

    def _has(c: str) -> bool:
        return c in df.columns

    if "order_id" not in df.columns or df["order_id"].isna().all():
        if "user_id" in df.columns and "sale_date" in df.columns:
            base = (
                df["user_id"].astype(str)
                + "_"
                + pd.to_datetime(df["sale_date"], errors="coerce").dt.strftime("%Y%m%d")
            )
            if "store_id" in df.columns:
                base = df["store_id"].astype(str) + "_" + base
            df["order_id"] = base
            df["order_id_source"] = "generated_from_user_date"
            rules.append("pseudo_order_id_generation")
        else:
            df["order_id_source"] = "unavailable"
    else:
        df["order_id_source"] = "original"

    if _has("amount") and _has("quantity") and _has("unit_price"):
        m = df["amount"].isna() & df["quantity"].notna() & df["unit_price"].notna()
        df.loc[m, "amount"] = df.loc[m, "quantity"] * df.loc[m, "unit_price"]
        m = df["quantity"].isna() & df["amount"].notna() & (df.get("unit_price", 0) > 0)
        df.loc[m, "quantity"] = df.loc[m, "amount"] / df.loc[m, "unit_price"]
        m = df["unit_price"].isna() & df["amount"].notna() & (df["quantity"] != 0)
        df.loc[m, "unit_price"] = df.loc[m, "amount"] / df.loc[m, "quantity"]
        rules.append("amount_qty_price_complete")
    elif _has("amount") and _has("quantity") and not _has("unit_price"):
        df["unit_price"] = (df["amount"] / df["quantity"].replace(0, np.nan)).round(4)
        df["unit_price_source"] = "derived_amount_div_qty"
        rules.append("unit_price_derived")
    elif _has("amount") and _has("unit_price") and not _has("quantity"):
        df["quantity"] = (df["amount"] / df["unit_price"].replace(0, np.nan)).round(4)
        rules.append("quantity_derived")

    if _has("unit_price") and _has("item_id"):
        bad = df["unit_price"].isna() | (df["unit_price"] <= 0)
        if bad.any():
            good = df.loc[~bad]
            item_med = good.groupby("item_id")["unit_price"].median()
            l3_med = (
                good.groupby("cat_l3_name")["unit_price"].median() if _has("cat_l3_name") else None
            )
            gmed = good["unit_price"].median()
            for i in df.index[bad]:
                v = item_med.get(df.at[i, "item_id"], np.nan)
                if pd.isna(v) and l3_med is not None and _has("cat_l3_name"):
                    v = l3_med.get(df.at[i, "cat_l3_name"], np.nan)
                df.at[i, "unit_price"] = v if not pd.isna(v) else gmed
            rules.append("unit_price_impute")

    if _has("unit"):
        df["unit"] = df["unit"].map(lambda u: _norm_unit(u))
        rules.append("unit_normalization")

    if _has("amount") or _has("quantity"):
        q = df["quantity"] if _has("quantity") else pd.Series(1, index=df.index)
        a = df["amount"] if _has("amount") else pd.Series(1, index=df.index)
        df["is_return"] = ((q <= 0) | (a <= 0)).astype(int)
        rules.append("return_flagging")

    if "is_promo" not in df.columns and _has("discount"):
        df["is_promo"] = (df["discount"].fillna(0) > 0).astype("Int64")
        df["is_promo_source"] = "derived_from_discount"
        rules.append("promo_from_discount")

    if not _has("cat_l3_name"):
        if _has("cat_l2_name"):
            df["cat_l3_name"] = df["cat_l2_name"]
            rules.append("cat_l3_fallback_l2")
        elif _has("cat_l1_name"):
            df["cat_l3_name"] = df["cat_l1_name"]
            rules.append("cat_l3_fallback_l1")
        elif _has("item_name"):
            df["cat_l3_name"] = df["item_name"]
            rules.append("cat_l3_fallback_itemname")
        elif _has("item_id"):
            df["cat_l3_name"] = df["item_id"]
            rules.append("cat_l3_fallback_itemid")
    if not _has("cat_l1_name") and _has("cat_l3_name"):
        df["cat_l1_name"] = df["cat_l3_name"]
        rules.append("cat_l1_fallback_l3")

    if not _has("item_name") and _has("item_id"):
        df["item_name"] = df["item_id"]
        rules.append("item_name_fallback_id")

    return df, rules


def _norm_unit(u: Any) -> str:
    if pd.isna(u):
        return "未知单位"
    s = str(u).replace("　", "").strip()
    if s.lower() in UNIT_DIRTY:
        return "未知单位"
    return _UNIT_MAP.get(s.lower(), s if s else "未知单位")
