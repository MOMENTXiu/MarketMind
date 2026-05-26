"""Rank universal recommendations: multi-recall + CRITIC-TOPSIS fusion."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

from backend.abilities.universal_analysis.common import critic_weights, positive

K = 10
SIGNALS = ["graph", "cat", "pop"]


def _graph_embed(train: pd.DataFrame, dim: int = 32) -> dict[str, Any] | None:
    agg = (
        train.groupby(["user_id", "item_id"])
        .agg(f=("item_id", "size"), a=("amount", "sum"))
        .reset_index()
    )
    if agg["user_id"].nunique() < 5 or agg["item_id"].nunique() < 5:
        return None
    w = np.log1p(agg["f"]) + np.log1p(agg["a"].clip(lower=0))
    users = agg["user_id"].unique()
    items = agg["item_id"].unique()
    ui = {u: i for i, u in enumerate(users)}
    ii = {t: j for j, t in enumerate(items)}
    M = csr_matrix(
        (w, (agg["user_id"].map(ui), agg["item_id"].map(ii))),
        shape=(len(users), len(items)),
    )
    k = min(dim, min(M.shape) - 1)
    if k < 2:
        return None
    U, S, Vt = svds(M, k=k)
    return {
        "P": U * np.sqrt(S),
        "Q": Vt.T * np.sqrt(S),
        "uidx": ui,
        "inv": {j: t for t, j in ii.items()},
    }


def _build_signals(train: pd.DataFrame) -> tuple[Any, list[Any], list[Any]]:
    pop = train.groupby("item_id").agg(amt=("amount", "sum"), buyers=("user_id", "nunique"))
    popularity = np.log1p(pop["amt"]) + np.log1p(pop["buyers"])
    popularity = popularity / (popularity.max() + 1e-9)
    pop_top = popularity.sort_values(ascending=False)
    item_l1 = (
        train.drop_duplicates("item_id").set_index("item_id")["cat_l1_name"]
        if "cat_l1_name" in train.columns
        else None
    )
    u_l1 = (
        train.groupby(["user_id", "cat_l1_name"])["amount"].sum() if item_l1 is not None else None
    )
    gemb = _graph_embed(train)
    pop_seed = pop_top.head(30)

    def score_fn(u: str) -> dict[str, dict[str, float]]:
        c: dict[str, dict[str, float]] = {}
        for it in pop_seed.index:
            c.setdefault(it, {})
        if gemb and u in gemb["uidx"]:
            sc = gemb["Q"] @ gemb["P"][gemb["uidx"][u]]
            top = np.argsort(-sc)[:80]
            mn, mx = sc[top].min(), sc[top].max()
            for j in top:
                c.setdefault(gemb["inv"][j], {})["graph"] = float((sc[j] - mn) / (mx - mn + 1e-9))
        if u_l1 is not None:
            try:
                prefs = u_l1.loc[u].sort_values(ascending=False)
                for l1, pv in prefs.head(3).items():
                    items_c = item_l1.index[item_l1 == l1]
                    for it, pvv in pop_top[pop_top.index.isin(items_c)].head(20).items():
                        c.setdefault(it, {})["cat"] = max(
                            c.get(it, {}).get("cat", 0),
                            float(pv) / (prefs.iloc[0] + 1e-9) * float(pvv),
                        )
            except KeyError:
                pass
        for it in c:
            c[it]["pop"] = float(popularity.get(it, 0))
        return c

    return score_fn, pop_top.head(K).index.tolist(), list(popularity.index)


def _rank_single(
    c: dict[str, dict[str, float]], sig: str, glob: list[Any], n: int = K
) -> list[Any]:
    items = [i for i in c if c[i].get(sig, 0) > 0]
    return sorted(items, key=lambda i: c[i][sig], reverse=True)[:n] or glob


def _reliability(train: pd.DataFrame) -> dict[str, float]:
    cut = train["sale_date"].quantile(0.8)
    itr = train[train["sale_date"] <= cut]
    iva = train[train["sale_date"] > cut]
    truth = iva.groupby("user_id")["item_id"].apply(set).to_dict()
    tru = set(itr["user_id"].unique())
    users = [u for u in truth if u in tru]
    if len(users) < 20 or itr.empty:
        return {s: 1.0 for s in SIGNALS}
    if len(users) > 400:
        users = list(np.random.default_rng(0).choice(users, 400, replace=False))
    sf, glob, _ = _build_signals(itr)
    rel = {s: 0.0 for s in SIGNALS}
    for u in users:
        c = sf(u)
        t = truth[u]
        for s in SIGNALS:
            rec = _rank_single(c, s, glob)
            rel[s] += len(set(rec) & t) / max(len(t), 1)
    mx = max(rel.values()) + 1e-9
    return {s: rel[s] / mx for s in SIGNALS}


def _evaluate(
    rec_dict: dict[str, list[Any]], truth: dict[str, set[Any]], all_items: list[Any], name: str
) -> dict[str, Any]:
    P = R = H = N = n = 0
    union = set()
    for u, rec in rec_dict.items():
        t = truth.get(u, set())
        if not t:
            continue
        n += 1
        topk = rec[:K]
        hit = len(set(topk) & t)
        P += hit / K
        R += hit / len(t)
        H += 1 if hit else 0
        dcg = sum(1 / np.log2(r + 2) for r, i in enumerate(topk) if i in t)
        idcg = sum(1 / np.log2(r + 2) for r in range(min(len(t), K)))
        N += dcg / idcg if idcg else 0
        union |= set(topk)
    n = max(n, 1)
    return {
        "模型": name,
        "Precision@10": round(P / n, 4),
        "Recall@10": round(R / n, 4),
        "HitRate@10": round(H / n, 4),
        "NDCG@10": round(N / n, 4),
        "Coverage": round(len(union) / max(len(all_items), 1), 4),
    }


def rank_universal_recommendations(df: pd.DataFrame, _cap: dict[str, Any]) -> dict[str, Any]:
    """Return recommendation result dict with eval metrics."""
    pos = positive(df)
    if not ({"user_id", "item_id", "amount"} <= set(pos.columns)):
        return {"status": "skipped", "reason": "缺 user_id/item_id/amount"}
    if "sale_date" not in pos.columns:
        return {"status": "skipped", "reason": "缺 sale_date"}

    cut = pos["sale_date"].quantile(0.8)
    train = pos[pos["sale_date"] <= cut]
    test = pos[pos["sale_date"] > cut]
    truth = test.groupby("user_id")["item_id"].apply(set).to_dict()
    tru = set(train["user_id"].unique())
    eval_users = [u for u in truth if u in tru]
    if len(eval_users) < 10:
        return {
            "status": "skipped",
            "reason": f"复购评估用户仅 {len(eval_users)}，时间外推不可靠",
        }

    reliability = _reliability(train)
    score_fn, glob, all_items = _build_signals(train)

    models: dict[str, dict[str, list[Any]]] = {
        "热门": {},
        "类目偏好": {},
        "图嵌入": {},
        "CRITIC-TOPSIS": {},
    }
    for u in eval_users:
        c = score_fn(u)
        models["热门"][u] = glob
        models["类目偏好"][u] = _rank_single(c, "cat", glob)
        models["图嵌入"][u] = _rank_single(c, "graph", glob)
        if len(c) >= 2:
            items = list(c)
            X = np.array([[c[i].get(s, 0) for s in SIGNALS] for i in items], float)
            if X.std(axis=0).sum() > 0:
                w = critic_weights(X) * np.array([reliability[s] for s in SIGNALS])
                w = w / (w.sum() + 1e-9)
                Z = (X - X.min(0)) / (X.max(0) - X.min(0) + 1e-9)
                fused = Z @ w
                models["CRITIC-TOPSIS"][u] = [items[j] for j in np.argsort(-fused)][:K]
            else:
                models["CRITIC-TOPSIS"][u] = glob
        else:
            models["CRITIC-TOPSIS"][u] = glob

    ev = pd.DataFrame([_evaluate(models[m], truth, all_items, m) for m in models])
    fusion = float(ev[ev["模型"] == "CRITIC-TOPSIS"]["HitRate@10"].iloc[0])
    best_single = ev[ev["模型"] != "CRITIC-TOPSIS"]["HitRate@10"].max()
    return {
        "status": "ok",
        "eval_users": len(eval_users),
        "reliability": {k: round(v, 3) for k, v in reliability.items()},
        "best_model": ev.loc[ev["HitRate@10"].idxmax(), "模型"],
        "fusion_hit": round(fusion, 4),
        "best_single_hit": round(float(best_single), 4),
        "fusion_vs_best": round(fusion - float(best_single), 4),
        "evaluation": ev.to_dict("records"),
    }
