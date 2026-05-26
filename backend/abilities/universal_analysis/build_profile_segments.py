"""Build customer profile (RFM+) and cluster segments."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from backend.abilities.universal_analysis.common import positive


def build_profile_segments(df: pd.DataFrame, _cap: dict[str, Any]) -> dict[str, Any]:
    """Return profile/segmentation result dict."""
    pos = positive(df)

    def _has(c: str) -> bool:
        return c in pos.columns

    if not _has("user_id"):
        return {"status": "skipped", "reason": "缺少 user_id"}

    Dmax = pos["sale_date"].max() if _has("sale_date") else pd.Timestamp.now()
    g = pos.groupby("user_id")
    prof = pd.DataFrame(index=sorted(pos["user_id"].unique()))
    prof.index.name = "user_id"

    if _has("sale_date"):
        prof["R_最近间隔"] = (Dmax - g["sale_date"].max()).dt.days
    prof["F_频次"] = g["order_id"].nunique() if _has("order_id") else g["sale_date"].nunique()
    prof["M_金额"] = g["amount"].sum() if _has("amount") else g.size()
    prof["记录数"] = g.size()
    prof["客单价"] = prof["M_金额"] / prof["F_频次"].clip(lower=1)
    if _has("quantity"):
        prof["总数量"] = g["quantity"].sum()
    if _has("cat_l1_name") and _has("amount"):
        piv = pos.pivot_table(
            index="user_id", columns="cat_l1_name", values="amount", aggfunc="sum", fill_value=0
        )
        p = piv.div(piv.sum(axis=1) + 1e-9, axis=0).values
        prof["类目熵"] = -np.nansum(np.where(p > 0, p * np.log(p), 0), axis=1)
    if _has("is_promo") and _has("amount"):
        pa = pos[pos["is_promo"] == 1].groupby("user_id")["amount"].sum()
        prof["促销金额占比"] = (pa / prof["M_金额"]).reindex(prof.index).fillna(0)
    if _has("discount"):
        prof["平均折扣"] = g["discount"].mean()
    if _has("profit"):
        prof["利润率"] = (g["profit"].sum() / prof["M_金额"].replace(0, np.nan)).fillna(0)
    if _has("age"):
        prof["年龄"] = g["age"].first().astype(float)

    prof = prof.reset_index()
    feats = [c for c in prof.columns if c != "user_id"]

    Xdf = prof[feats].copy()
    for c in ["F_频次", "M_金额", "记录数", "客单价", "总数量"]:
        if c in Xdf:
            Xdf[c] = np.log1p(Xdf[c].clip(lower=0))
    Xs = StandardScaler().fit_transform(Xdf.fillna(Xdf.median()).values)

    idx = np.random.default_rng(42).choice(len(Xs), min(5000, len(Xs)), replace=False)
    scan, models = [], {}
    for k in range(2, 8):
        km = KMeans(k, n_init=5, random_state=42).fit(Xs)
        sil = silhouette_score(Xs[idx], km.labels_[idx])
        dbi = davies_bouldin_score(Xs, km.labels_)
        scan.append({"k": k, "轮廓系数": round(sil, 4), "DB指数": round(dbi, 4)})
        models[k] = (sil, km)

    n_users = len(prof)
    lo, hi = (3, 6) if n_users >= 200 else (2, 3)
    K = max(range(lo, hi + 1), key=lambda k: models[k][0])
    sil, km = models[K]
    prof["分群"] = km.labels_

    aggd = {"人数": ("user_id", "size")}
    for c in feats:
        aggd[c] = (c, "mean")
    sp = prof.groupby("分群").agg(**aggd).round(3)
    sp["人数占比"] = (sp["人数"] / len(prof)).round(3)
    if "M_金额" in sp:
        sp["销售贡献占比"] = (
            (sp["人数"] * sp["M_金额"]) / (sp["人数"] * sp["M_金额"]).sum()
        ).round(3)

    return {
        "status": "ok",
        "n_segments": int(K),
        "silhouette": round(sil, 4),
        "top_contrib_seg": int(sp["销售贡献占比"].idxmax()) if "销售贡献占比" in sp else None,
        "features_used": feats,
        "segment_profiles": sp.reset_index().to_dict("records"),
        "customer_segments": prof[["user_id", "分群"]].to_dict("records"),
        "kscan": scan,
        "model": {"kmeans": km, "feats": feats},
    }
