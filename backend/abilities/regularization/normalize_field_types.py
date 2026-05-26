"""Type normalization: dates, numerics, binaries, ids, cats."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.abilities.regularization.field_aliases import PROMO_FALSE, PROMO_TRUE, STANDARD_SCHEMA


def _clean_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(",", "", regex=False).str.replace("￥", "", regex=False)
    s = s.str.replace("¥", "", regex=False).str.replace("元", "", regex=False)
    s = s.str.replace("%", "", regex=False)
    neg = s.str.startswith("(") & s.str.endswith(")")
    s = s.where(~neg, "-" + s.str.slice(1, -1))
    return pd.to_numeric(s, errors="coerce")


def _parse_dates(series: pd.Series) -> pd.Series:
    raw = series.astype(str).str.strip()
    is_ym = raw.str.fullmatch(r"\d{6}")
    out = pd.to_datetime(raw, errors="coerce", format="mixed", dayfirst=False)
    if is_ym.any():
        ym = pd.to_datetime(raw.where(is_ym) + "01", format="%Y%m%d", errors="coerce")
        out = out.fillna(ym)
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


def normalize_field_types(
    raw_df: pd.DataFrame,
    mapping: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return (normalized dataframe, type stats)."""
    df = pd.DataFrame(index=raw_df.index)
    stats: dict[str, Any] = {
        "date_parsed_rate": None,
        "numeric_coerced": {},
        "promo_parsed_rate": None,
    }
    for raw, std in mapping.items():
        col = raw_df[raw]
        typ = STANDARD_SCHEMA[std][2]
        if typ == "date":
            d = _parse_dates(col)
            df[std] = d
            stats["date_parsed_rate"] = round(float(d.notna().mean()), 4)
        elif typ == "num":
            v = _clean_numeric(col)
            df[std] = v
            stats["numeric_coerced"][std] = int(v.isna().sum())
        elif typ == "binary":
            b, rate = _to_binary(col)
            df[std] = b
            stats["promo_parsed_rate"] = rate
        elif typ == "id":
            df[std] = col.astype(str).str.strip().replace({"nan": np.nan})
        else:
            df[std] = col.astype(str).str.strip().replace({"nan": np.nan})

    if "sale_date" in df.columns:
        d = pd.to_datetime(df["sale_date"], errors="coerce")
        df["sale_year"] = d.dt.year
        df["sale_month"] = d.dt.month
        df["sale_day"] = d.dt.day
        df["weekday"] = d.dt.weekday
        df["is_weekend"] = (d.dt.weekday >= 5).astype("Int64")
        df["week_of_year"] = d.dt.isocalendar().week.astype("Int64")
        df["quarter"] = d.dt.quarter
    return df, stats


def _to_binary(col: pd.Series) -> tuple[pd.Series, float]:
    s = col.astype(str).str.strip().str.lower()

    def m(v: str) -> int:
        if v in PROMO_TRUE:
            return 1
        if v in PROMO_FALSE:
            return 0
        return 1

    out = s.map(m)
    parsed = s.isin(PROMO_TRUE | PROMO_FALSE).mean()
    return out.astype("Int64"), round(float(parsed), 4)
