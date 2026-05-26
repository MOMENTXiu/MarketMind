# -*- coding: utf-8 -*-
"""TypeNormalizer：类型正则化（设计报告 §9、§17.4）。
按映射把原始列改名为标准字段，并做日期/数值/促销/ID 的类型规范化与时间派生。"""
import re
import warnings
import numpy as np
import pandas as pd
from .field_aliases import STANDARD_SCHEMA, PROMO_TRUE, PROMO_FALSE
warnings.filterwarnings("ignore")


def clean_numeric(series):
    s = series.astype(str).str.strip()
    s = s.str.replace(",", "", regex=False).str.replace("￥", "", regex=False)
    s = s.str.replace("¥", "", regex=False).str.replace("元", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    # 括号负数 (25.6) -> -25.6
    neg = s.str.startswith("(") & s.str.endswith(")")
    s = s.where(~neg, "-" + s.str.slice(1, -1))
    return pd.to_numeric(s, errors="coerce")


def parse_dates(series):
    """多格式日期解析 + 非法日期(非闰年2/29等)订正。"""
    raw = series.astype(str).str.strip()
    # 纯 6 位 yyyymm -> 当月1日
    is_ym = raw.str.fullmatch(r"\d{6}")
    out = pd.to_datetime(raw, errors="coerce", format="mixed", dayfirst=False)
    if is_ym.any():
        ym = pd.to_datetime(raw.where(is_ym) + "01", format="%Y%m%d", errors="coerce")
        out = out.fillna(ym)
    # 仍失败的：尝试订正非法日（如 20250229 -> 当月最后一天）
    bad = out.isna() & raw.str.fullmatch(r"\d{8}")
    for i in series.index[bad.fillna(False)]:
        sv = raw[i]
        try:
            y, m = int(sv[:4]), int(sv[4:6])
            last = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(1)
            out[i] = last
        except Exception:
            pass
    return out


class TypeNormalizer:
    def normalize(self, raw_df, mapping):
        """mapping: raw->std。返回标准列名 DataFrame + 处理统计。"""
        df = pd.DataFrame(index=raw_df.index)
        stats = {"date_parsed_rate": None, "numeric_coerced": {}, "promo_parsed_rate": None}
        for raw, std in mapping.items():
            col = raw_df[raw]
            typ = STANDARD_SCHEMA[std][2]
            if typ == "date":
                d = parse_dates(col)
                df[std] = d
                stats["date_parsed_rate"] = round(float(d.notna().mean()), 4)
            elif typ == "num":
                v = clean_numeric(col)
                df[std] = v
                stats["numeric_coerced"][std] = int(v.isna().sum())
            elif typ == "binary":
                b, rate = self._to_binary(col)
                df[std] = b
                stats["promo_parsed_rate"] = rate
            elif typ == "id":
                df[std] = col.astype(str).str.strip().replace({"nan": np.nan})
            else:  # cat / text
                df[std] = col.astype(str).str.strip().replace({"nan": np.nan})

        # 时间派生
        if "sale_date" in df.columns:
            d = df["sale_date"]
            df["sale_year"] = d.dt.year
            df["sale_month"] = d.dt.month
            df["sale_day"] = d.dt.day
            df["weekday"] = d.dt.weekday
            df["is_weekend"] = (d.dt.weekday >= 5).astype("Int64")
            df["week_of_year"] = d.dt.isocalendar().week.astype("Int64")
            df["quarter"] = d.dt.quarter
        return df, stats

    def _to_binary(self, col):
        s = col.astype(str).str.strip().str.lower()
        def m(v):
            if v in PROMO_TRUE:
                return 1
            if v in PROMO_FALSE:
                return 0
            return 1  # 其它非空值（如具体活动类型名）视为促销
        out = s.map(m)
        parsed = s.isin(PROMO_TRUE | PROMO_FALSE).mean()
        return out.astype("Int64"), round(float(parsed), 4)
