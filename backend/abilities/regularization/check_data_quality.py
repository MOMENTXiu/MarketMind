"""Data quality assessment: coverage, validity, completeness, volume scores."""

from __future__ import annotations

from typing import Any

import numpy as np

from backend.abilities.regularization.field_aliases import FIELD_WEIGHTS

CORE = ["user_id", "sale_date", "item_id", "amount"]


def check_data_quality(
    raw_df: Any,
    norm_df: Any,
    mapping: dict[str, str],
    dup_removed: int = 0,
) -> dict[str, Any]:
    """Return quality report dict."""
    n_raw = len(raw_df)
    n = len(norm_df)
    avail = [c for c in norm_df.columns]

    missing: dict[str, float | None] = {}
    for c in CORE + ["quantity", "unit_price", "order_id"]:
        if c in norm_df.columns:
            missing[c] = round(float(norm_df[c].isna().mean()), 4)

    invalid_date = (
        int(norm_df["sale_date"].isna().sum()) if "sale_date" in norm_df.columns else None
    )
    invalid_amount = (
        int((norm_df["amount"].isna() | (norm_df["amount"] <= 0)).sum())
        if "amount" in norm_df.columns
        else None
    )
    invalid_id = int(norm_df["user_id"].isna().sum()) if "user_id" in norm_df.columns else None

    wsum = sum(FIELD_WEIGHTS.values())
    s_field = sum(w for f, w in FIELD_WEIGHTS.items() if f in norm_df.columns) / wsum
    bad = sum(x for x in [invalid_date, invalid_amount, invalid_id] if x is not None and x > 0) or 0
    s_valid = 1 - bad / max(n * 3, 1)
    core_miss = (
        np.mean([missing.get(c, 1.0) for c in CORE if c in norm_df.columns])
        if any(c in norm_df.columns for c in CORE)
        else 1.0
    )
    s_complete = 1 - core_miss
    s_volume = min(1.0, np.log10(max(n, 1)) / 4.0)
    ready = 100 * (0.4 * s_field + 0.3 * s_valid + 0.2 * s_complete + 0.1 * s_volume)

    grade = "优秀" if ready >= 85 else "良好" if ready >= 70 else "一般" if ready >= 50 else "较差"
    return {
        "raw_rows": n_raw,
        "normalized_rows": n,
        "duplicate_rows_removed": int(dup_removed),
        "mapped_field_count": len(mapping),
        "available_standard_fields": avail,
        "missing_rates": missing,
        "invalid_date_count": invalid_date,
        "invalid_amount_count": invalid_amount,
        "invalid_user_id_count": invalid_id,
        "return_rows": int(norm_df["is_return"].sum()) if "is_return" in norm_df.columns else 0,
        "scores": {
            "S_field": round(s_field, 4),
            "S_valid": round(s_valid, 4),
            "S_complete": round(s_complete, 4),
            "S_volume": round(s_volume, 4),
        },
        "analysis_ready_score": round(ready, 1),
        "grade": grade,
    }
