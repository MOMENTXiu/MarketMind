"""Schema profiler: per-column dtype/missing/unique/sample/pattern stats."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

DATE_RE = [
    (re.compile(r"^\d{8}$"), "yyyymmdd"),
    (re.compile(r"^\d{6}$"), "yyyymm"),
    (re.compile(r"^\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}"), "yyyy-mm-dd"),
    (re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日"), "yyyy年mm月dd日"),
]


def _clean_num(v: Any) -> str:
    s = (
        str(v)
        .strip()
        .replace(",", "")
        .replace("￥", "")
        .replace("¥", "")
        .replace("元", "")
        .replace("%", "")
    )
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    return s


def _is_number(v: Any) -> bool:
    try:
        float(_clean_num(v))
        return True
    except (ValueError, TypeError):
        return False


def profile_source_schema(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Return a profile dict mapping column name to stats dict."""
    prof: dict[str, dict[str, Any]] = {}
    n = len(df)
    for col in df.columns:
        s = df[col]
        nonnull = s.dropna().astype(str).str.strip()
        nonnull = nonnull[nonnull != ""]
        vals = nonnull.tolist()
        sample = vals[:5]
        num_rate = np.mean([_is_number(v) for v in vals]) if vals else 0.0
        date_rate, pat = _date_rate(vals)
        uniq = s.nunique(dropna=True)
        prof[str(col)] = {
            "dtype": str(s.dtype),
            "missing_rate": round(1 - len(nonnull) / n, 4) if n else 1.0,
            "n_unique": int(uniq),
            "unique_ratio": round(uniq / max(len(nonnull), 1), 4),
            "numeric_rate": round(float(num_rate), 4),
            "date_rate": round(float(date_rate), 4),
            "date_pattern": pat,
            "is_binary": uniq <= 3,
            "avg_len": round(float(np.mean([len(str(v)) for v in vals])) if vals else 0, 1),
            "sample_values": sample,
            "min": _safe_min(vals, num_rate),
            "max": _safe_max(vals, num_rate),
        }
    return prof


def _date_rate(vals: list[Any]) -> tuple[float, str | None]:
    if not vals:
        return 0.0, None
    hit, pat = 0, None
    for v in vals[:200]:
        sv = str(v).strip()
        for rgx, name in DATE_RE:
            if rgx.match(sv):
                hit += 1
                pat = pat or name
                break
    try:
        parsed = pd.to_datetime(pd.Series(vals[:200]), errors="coerce")
        pr = parsed.notna().mean()
        if pr > hit / min(len(vals), 200):
            return float(pr), pat or "parsable"
    except Exception:
        pass
    return hit / min(len(vals), 200), pat


def _safe_min(vals: list[Any], num_rate: float) -> float | None:
    if num_rate > 0.8 and vals:
        try:
            return float(min(float(_clean_num(v)) for v in vals[:1000]))
        except Exception:
            return None
    return None


def _safe_max(vals: list[Any], num_rate: float) -> float | None:
    if num_rate > 0.8 and vals:
        try:
            return float(max(float(_clean_num(v)) for v in vals[:1000]))
        except Exception:
            return None
    return None
