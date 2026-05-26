# -*- coding: utf-8 -*-
"""BusinessNormalizer：业务正则化（设计报告 §10、§17.5）。
订单号补全(pseudo)、金额/数量/单价互补、单位归一、退货标记、促销/类目兜底。"""
import numpy as np
import pandas as pd
from .field_aliases import UNIT_ALIASES, UNIT_DIRTY

_UNIT_MAP = {}
for std, al in UNIT_ALIASES.items():
    for a in al:
        _UNIT_MAP[str(a).strip().lower()] = std


class BusinessNormalizer:
    def normalize(self, df):
        df = df.copy()
        rules = []  # 记录已应用的业务规则

        # 1) 订单号补全
        if "order_id" not in df.columns or df["order_id"].isna().all():
            if "user_id" in df.columns and "sale_date" in df.columns:
                base = df["user_id"].astype(str) + "_" + df["sale_date"].dt.strftime("%Y%m%d")
                if "store_id" in df.columns:
                    base = df["store_id"].astype(str) + "_" + base
                df["order_id"] = base
                df["order_id_source"] = "generated_from_user_date"
                rules.append("pseudo_order_id_generation")
            else:
                df["order_id_source"] = "unavailable"
        else:
            df["order_id_source"] = "original"

        # 2) 金额/数量/单价互补
        has = lambda c: c in df.columns
        if has("amount") and has("quantity") and has("unit_price"):
            m = df["amount"].isna() & df["quantity"].notna() & df["unit_price"].notna()
            df.loc[m, "amount"] = df.loc[m, "quantity"] * df.loc[m, "unit_price"]
            m = df["quantity"].isna() & df["amount"].notna() & (df.get("unit_price", 0) > 0)
            df.loc[m, "quantity"] = df.loc[m, "amount"] / df.loc[m, "unit_price"]
            m = df["unit_price"].isna() & df["amount"].notna() & (df["quantity"] != 0)
            df.loc[m, "unit_price"] = df.loc[m, "amount"] / df.loc[m, "quantity"]
            rules.append("amount_qty_price_complete")
        elif has("amount") and has("quantity") and not has("unit_price"):
            df["unit_price"] = (df["amount"] / df["quantity"].replace(0, np.nan)).round(4)
            df["unit_price_source"] = "derived_amount_div_qty"
            rules.append("unit_price_derived")
        elif has("amount") and has("unit_price") and not has("quantity"):
            df["quantity"] = (df["amount"] / df["unit_price"].replace(0, np.nan)).round(4)
            rules.append("quantity_derived")

        # 3) 单价异常填补（同商品→同小类→全局中位数）
        if has("unit_price") and has("item_id"):
            bad = df["unit_price"].isna() | (df["unit_price"] <= 0)
            if bad.any():
                good = df.loc[~bad]
                item_med = good.groupby("item_id")["unit_price"].median()
                l3_med = good.groupby("cat_l3_name")["unit_price"].median() if has("cat_l3_name") else None
                gmed = good["unit_price"].median()
                for i in df.index[bad]:
                    v = item_med.get(df.at[i, "item_id"], np.nan)
                    if pd.isna(v) and l3_med is not None and has("cat_l3_name"):
                        v = l3_med.get(df.at[i, "cat_l3_name"], np.nan)
                    df.at[i, "unit_price"] = v if not pd.isna(v) else gmed
                rules.append("unit_price_impute")

        # 4) 单位归一
        if has("unit"):
            df["unit"] = df["unit"].map(lambda u: self._norm_unit(u))
            rules.append("unit_normalization")

        # 5) 退货 / 异常标记
        if has("amount") or has("quantity"):
            q = df["quantity"] if has("quantity") else pd.Series(1, index=df.index)
            a = df["amount"] if has("amount") else pd.Series(1, index=df.index)
            df["is_return"] = ((q <= 0) | (a <= 0)).astype(int)
            rules.append("return_flagging")

        # 6) 促销兜底：无 is_promo 但有 discount → discount>0 视为促销
        if "is_promo" not in df.columns and has("discount"):
            df["is_promo"] = (df["discount"].fillna(0) > 0).astype("Int64")
            df["is_promo_source"] = "derived_from_discount"
            rules.append("promo_from_discount")

        # 7) 类目层级兜底
        if not has("cat_l3_name"):
            if has("cat_l2_name"):
                df["cat_l3_name"] = df["cat_l2_name"]; rules.append("cat_l3_fallback_l2")
            elif has("cat_l1_name"):
                df["cat_l3_name"] = df["cat_l1_name"]; rules.append("cat_l3_fallback_l1")
            elif has("item_name"):
                df["cat_l3_name"] = df["item_name"]; rules.append("cat_l3_fallback_itemname")
            elif has("item_id"):
                df["cat_l3_name"] = df["item_id"]; rules.append("cat_l3_fallback_itemid")
        if not has("cat_l1_name") and has("cat_l3_name"):
            df["cat_l1_name"] = df["cat_l3_name"]; rules.append("cat_l1_fallback_l3")

        # 8) 商品显示名兜底
        if not has("item_name") and has("item_id"):
            df["item_name"] = df["item_id"]; rules.append("item_name_fallback_id")

        return df, rules

    def _norm_unit(self, u):
        if pd.isna(u):
            return "未知单位"
        s = str(u).replace("　", "").strip()
        if s.lower() in UNIT_DIRTY:
            return "未知单位"
        return _UNIT_MAP.get(s.lower(), s if s else "未知单位")
