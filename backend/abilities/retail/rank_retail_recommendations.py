"""Rank retail recommendations using multi-recall signals and CRITIC-TOPSIS fusion."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.abilities.retail.build_retail_recommendation_signals import (
    RetailRecommendationSignals,
)
from backend.abilities.retail.rank_by_critic_topsis import critic_weights, topsis

SIGNAL_COLS = ["graph", "rule", "cat", "cycle", "promo", "price", "pop"]

REASON_MAP = {
    "graph": "与你购买行为相似的顾客也常购买该商品",
    "rule": "与你近期购买商品强关联",
    "cat": "你长期偏好该类目",
    "cycle": "你可能接近该商品的复购周期",
    "promo": "你对促销较敏感，该商品促销适配度高",
    "price": "该商品符合你的常购价格带",
    "pop": "当前热销商品",
}


def _score_candidates(
    user_id: str,
    signals: RetailRecommendationSignals,
    top_pool: int,
) -> dict:
    """Build per-item signal score dict for a single user."""
    cand: dict = {}

    def ensure(item: str) -> None:
        if item not in cand:
            cand[item] = {s: 0.0 for s in SIGNAL_COLS}

    # ── graph (SVD collaborative filtering) ────────────────────────────────
    if signals.graph_embeddings and user_id in signals.graph_embeddings["uidx"]:
        ge = signals.graph_embeddings
        pu = ge["P"][ge["uidx"][user_id]]
        scores = ge["Q"] @ pu
        topg = np.argsort(-scores)[:120]
        s_min = scores[topg].min()
        s_max = scores[topg].max()
        for j in topg:
            it = ge["iidx_inv"][j]
            ensure(it)
            cand[it]["graph"] = float((scores[j] - s_min) / (s_max - s_min + 1e-9))

    # ── cat (category preference) ────────────────────────────────────────
    try:
        upref = signals.user_l3_preferences.loc[user_id].sort_values(ascending=False).head(8)
        for l3c, p in upref.items():
            items_c = signals.user_l3_code_items.get(l3c, set())
            sub = (
                signals.popularity[signals.popularity.index.isin(items_c)]
                .sort_values(ascending=False)
                .head(20)
            )
            for it, pv in sub.items():
                ensure(it)
                cand[it]["cat"] = max(cand[it]["cat"], float(p) * float(pv))
    except (KeyError, TypeError, AttributeError):
        pass

    # ── rule (item + l3 association) ─────────────────────────────────────
    u_items = signals.user_items.get(user_id, set())
    u_l3set = signals.user_l3_name_set.get(user_id, set())

    for ante, cons_list in signals.item_scoring_rules.items():
        if ante <= u_items:
            for cons, sc in cons_list:
                ensure(cons)
                cand[cons]["rule"] = max(cand[cons]["rule"], sc)

    for ante, cons_list in signals.l3_scoring_rules.items():
        if ante <= u_l3set:
            for cons_l3, sc in cons_list:
                items_c = set(signals.item_meta.index[signals.item_meta["cat_l3_name"] == cons_l3])
                sub = (
                    signals.popularity[signals.popularity.index.isin(items_c)]
                    .sort_values(ascending=False)
                    .head(8)
                )
                for it, pv in sub.items():
                    ensure(it)
                    cand[it]["rule"] = max(cand[it]["rule"], sc * 0.3)

    # ── cycle (repurchase) ───────────────────────────────────────────────
    for (uu, l3c), need in signals.repurchase_need.items():
        if uu != user_id:
            continue
        score = min(need, 2.0) / 2.0
        items_c = signals.user_l3_code_items.get(l3c, set())
        sub = (
            signals.popularity[signals.popularity.index.isin(items_c)]
            .sort_values(ascending=False)
            .head(10)
        )
        for it, pv in sub.items():
            ensure(it)
            cand[it]["cycle"] = max(cand[it]["cycle"], score)

    # ── cold-start fallback ──────────────────────────────────────────────
    if not cand:
        for it in signals.pop_rank_items.head(top_pool).index:
            ensure(it)

    # ── promo + price + pop (for all candidates) ─────────────────────────
    psens = float(
        signals.user_promo_sensitivity.get(user_id, 0.0)
        if hasattr(signals.user_promo_sensitivity, "get")
        else signals.user_promo_sensitivity.get(user_id, 0.0)
        if user_id in signals.user_promo_sensitivity.index
        else 0.0
    )
    ppref = float(
        signals.user_price_preference.get(user_id, 0.5)
        if user_id in signals.user_price_preference.index
        else 0.5
    )

    for it in cand:
        pr_rate = (
            float(signals.item_meta.loc[it, "promo_rate"]) if it in signals.item_meta.index else 0.0
        )
        cand[it]["promo"] = psens * pr_rate

        prk = float(signals.price_rank.get(it, 0.5) if it in signals.price_rank.index else 0.5)
        cand[it]["price"] = 1.0 - abs(ppref - prk)

        cand[it]["pop"] = float(
            signals.popularity.get(it, 0.0) if it in signals.popularity.index else 0.0
        )

    return cand


def _rank_topsis_fusion(
    cand: dict,
    reliability: dict[str, float] | None,
) -> tuple[list, np.ndarray, dict | None]:
    """Fuse multi-signal candidate scores via CRITIC-TOPSIS."""
    items = list(cand.keys())
    X = np.array([[cand[i][c] for c in SIGNAL_COLS] for i in items], float)

    if X.shape[0] < 2 or np.allclose(X.std(axis=0).sum(), 0):
        order = sorted(items, key=lambda i: cand[i]["pop"], reverse=True)
        return order, np.zeros(len(items)), None

    w_critic, _ = critic_weights(X)

    if reliability:
        rel = np.array([reliability.get(c, 1e-3) for c in SIGNAL_COLS], float)
        w = w_critic * rel
        w = w / (w.sum() + 1e-12)
    else:
        w = w_critic

    clo, _ = topsis(X, w)
    order = [items[j] for j in np.argsort(-clo)]
    return order, clo, dict(zip(SIGNAL_COLS, w))


def rank_retail_recommendations(
    signals: RetailRecommendationSignals,
    users: list[str],
    top_k: int = 10,
    reliability: dict[str, float] | None = None,
    top_pool: int = 250,
) -> pd.DataFrame:
    """Rank multi-recall candidates for each user and return top-k recommendations.

    Parameters
    ----------
    signals:
        Precomputed RetailRecommendationSignals.
    users:
        List of user IDs to generate recommendations for.
    top_k:
        Maximum number of recommendations per user.
    reliability:
        Optional per-signal reliability weights (signal name → weight).
    top_pool:
        Size of global popularity pool for cold-start fallback.

    Returns
    -------
    pd.DataFrame
        Columns: user_id, rank, item_id, cat_l3, score, 主要来源, reason
    """
    records = []

    for user_id in users:
        cand = _score_candidates(user_id, signals, top_pool)
        if not cand:
            continue

        order, clo_scores, weights = _rank_topsis_fusion(cand, reliability)
        clo_map = dict(zip(order, clo_scores)) if clo_scores is not None else {}

        for rank, it in enumerate(order[:top_k], start=1):
            # determine primary source
            if weights is not None:
                primary = max(
                    SIGNAL_COLS,
                    key=lambda s: cand[it][s] * weights.get(s, 0.0),
                )
            else:
                primary = max(SIGNAL_COLS, key=lambda s: cand[it][s])

            cat_l3 = (
                signals.item_meta.loc[it, "cat_l3_name"] if it in signals.item_meta.index else ""
            )
            score_val = float(clo_map.get(it, cand[it]["pop"]))

            records.append(
                {
                    "user_id": user_id,
                    "rank": rank,
                    "item_id": it,
                    "cat_l3": cat_l3,
                    "score": score_val,
                    "主要来源": primary,
                    "reason": REASON_MAP.get(primary, ""),
                }
            )

    return pd.DataFrame(
        records,
        columns=["user_id", "rank", "item_id", "cat_l3", "score", "主要来源", "reason"],
    )
