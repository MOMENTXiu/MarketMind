"""Estimate universal promotion effect: naive diff vs DML ATE."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder

from backend.abilities.universal_analysis.common import dml_ate, positive


def estimate_universal_promotion_effect(df: pd.DataFrame, _cap: dict[str, Any]) -> dict[str, Any]:
    """Return promotion analysis result dict."""
    pos = positive(df).copy()

    def _has(c: str) -> bool:
        return c in pos.columns

    out: dict[str, Any] = {}

    treat_col = "is_promo" if _has("is_promo") else None
    if treat_col is None or not _has("amount"):
        return {"status": "skipped", "reason": "缺 is_promo/amount"}

    ap = pos[pos[treat_col] == 1]["amount"].mean()
    an = pos[pos[treat_col] == 0]["amount"].mean()
    naive = ap - an
    out["naive_diff"] = round(naive, 3)

    Xparts: list[np.ndarray] = []
    cat_col = next((c for c in ["cat_l1_name", "cat_l3_name"] if _has(c)), None)
    if cat_col:
        ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore", min_frequency=30)
        Xparts.append(ohe.fit_transform(pos[[cat_col]]))
    for c in ["unit_price", "quantity", "sale_month", "weekday"]:
        if _has(c):
            Xparts.append(pos[[c]].fillna(0).values)
    theta = se = ci = None
    if Xparts:
        X = np.hstack(Xparts)
        T = pos[treat_col].values
        Y = pos["amount"].values
        try:
            theta, se, ci = dml_ate(X, T, Y, n_folds=5, discrete_treatment=True)
            out["dml_ate"] = round(theta, 3)
            out["dml_ci"] = [round(ci[0], 3), round(ci[1], 3)]
            out["dml_significant"] = bool(ci[0] * ci[1] > 0)
        except Exception as e:
            out["dml_error"] = str(e)[:60]

    if _has("discount"):
        dd = pos.groupby(
            pd.cut(
                pos["discount"],
                [-0.01, 0, 0.2, 0.4, 1.0],
                labels=["无", "0-0.2", "0.2-0.4", ">0.4"],
            ),
            observed=True,
        )["amount"].mean()
        out["discount_levels"] = dd.round(2).to_dict()
    if _has("profit"):
        out["total_profit"] = round(pos["profit"].sum(), 1)
        out["profit_margin"] = round(pos["profit"].sum() / pos["amount"].sum(), 4)

    return {"status": "ok", **out}
