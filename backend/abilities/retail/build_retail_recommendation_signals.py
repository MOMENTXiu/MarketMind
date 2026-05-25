"""Build multi-recall recommendation signals from training-period clean sales data."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.abilities.retail.rank_by_critic_topsis import critic_weights, topsis
from backend.core.errors import ValidationError

_REQUIRED_COLS = [
    "user_id",
    "sale_date",
    "item_id",
    "cat_l1_name",
    "cat_l2_name",
    "cat_l3_name",
    "cat_l3_code",
    "amount",
    "quantity",
    "is_return",
    "is_promo",
]


@dataclass(frozen=True)
class RetailRecommendationSignals:
    """All recall signals needed for multi-source recommendation ranking."""

    popularity: pd.Series
    pop_rank_items: pd.Series
    item_meta: pd.DataFrame
    price_rank: pd.Series
    user_l3_preferences: pd.Series
    user_total_amount: pd.Series
    user_promo_sensitivity: pd.Series
    user_price_preference: pd.Series
    user_items: dict
    user_l3_name_set: dict
    user_l3_code_items: dict
    repurchase_need: dict
    d_max: pd.Timestamp
    item_scoring_rules: dict
    l3_scoring_rules: dict
    graph_embeddings: dict | None


def _mine_scoring_rules(
    pos: pd.DataFrame,
    key: str,
    min_support: float,
    min_confidence: float,
    min_lift: float,
    max_len: int,
) -> dict:
    """Mine association-based scoring rules for recommendation candidate scoring."""
    from mlxtend.frequent_patterns import association_rules, fpgrowth
    from mlxtend.preprocessing import TransactionEncoder

    baskets = (
        pos.groupby(["user_id", "sale_date"])[key]
        .apply(lambda s: sorted(set(s)))
    )
    transactions = [t for t in baskets.tolist() if len(t) >= 2]
    if not transactions:
        return {}
    te = TransactionEncoder()
    arr = te.fit_transform(transactions)
    dfb = pd.DataFrame(arr, columns=te.columns_)
    freq = fpgrowth(dfb, min_support=min_support, use_colnames=True, max_len=max_len)
    if freq.empty:
        return {}
    rules = association_rules(freq, metric="confidence", min_threshold=min_confidence)
    rules = rules[
        (rules["lift"] >= min_lift) & (rules["consequents"].apply(len) == 1)
    ]
    d: dict = {}
    for _, row in rules.iterrows():
        ante = frozenset(row["antecedents"])
        cons = list(row["consequents"])[0]
        d.setdefault(ante, []).append((cons, float(row["confidence"] * row["lift"])))
    return d


def build_retail_recommendation_signals(
    train_df: pd.DataFrame,
    svd_dim: int = 48,
    time_decay: float = 0.02,
    rule_min_support: float = 0.003,
    rule_min_confidence: float = 0.20,
    rule_min_lift: float = 1.10,
) -> RetailRecommendationSignals:
    """Build all recall signals from training-period clean sales DataFrame.

    Parameters
    ----------
    train_df:
        Clean sales DataFrame matching the RetailV2 schema.
    svd_dim:
        Latent dimension for SVD graph embeddings.
    time_decay:
        Exponential time-decay coefficient for interaction weights.
    rule_min_support:
        Minimum support threshold for item association rules.
    rule_min_confidence:
        Minimum confidence threshold for association rules.
    rule_min_lift:
        Minimum lift threshold for association rules.

    Returns
    -------
    RetailRecommendationSignals
        Frozen dataclass with all recall and scoring signals.
    """
    missing = [c for c in _REQUIRED_COLS if c not in train_df.columns]
    if missing:
        raise ValidationError(f"Missing required columns: {missing}")

    pos = train_df[train_df["is_return"] == False].copy()  # noqa: E712

    # ── Popularity via CRITIC-TOPSIS ────────────────────────────────────────
    pg = pos.groupby("item_id").agg(
        amt=("amount", "sum"),
        qty=("quantity", "sum"),
        buyers=("user_id", "nunique"),
    )
    raw_x = np.log1p(pg[["amt", "qty", "buyers"]].clip(lower=0).values)
    w_pop, _ = critic_weights(raw_x)
    pop, _ = topsis(raw_x, w_pop)
    pg["popularity"] = pop
    popularity = pg["popularity"]

    pop_rank_items = popularity.sort_values(ascending=False)

    # ── item_meta ───────────────────────────────────────────────────────────
    meta_cols = ["item_id", "cat_l1_name", "cat_l2_name", "cat_l3_name", "cat_l3_code"]
    item_meta = (
        pos[meta_cols]
        .drop_duplicates("item_id")
        .set_index("item_id")
    )
    promo_rate = pos.groupby("item_id")["is_promo"].mean()
    item_meta = item_meta.copy()
    item_meta["promo_rate"] = promo_rate

    # ── price_rank ──────────────────────────────────────────────────────────
    ip = (
        pos.groupby(["cat_l3_code", "item_id"])["unit_price"]
        .mean()
        .reset_index()
    )
    ip["price_rank"] = ip.groupby("cat_l3_code")["unit_price"].rank(pct=True)
    price_rank = ip.set_index("item_id")["price_rank"]

    # ── user_l3_preferences ─────────────────────────────────────────────────
    u_l3 = pos.groupby(["user_id", "cat_l3_code"])["amount"].sum()
    u_tot = pos.groupby("user_id")["amount"].sum()
    user_l3_preferences = u_l3 / u_tot.reindex(u_l3.index, level="user_id")

    # ── user_total_amount + user_promo_sensitivity ──────────────────────────
    user_total_amount = u_tot
    promo_amt = pos[pos["is_promo"] == 1].groupby("user_id")["amount"].sum()
    user_promo_sensitivity = (promo_amt / u_tot).fillna(0)

    # ── user_price_preference ───────────────────────────────────────────────
    pos_pr = pos.merge(
        price_rank.rename("pr"), left_on="item_id", right_index=True, how="left"
    )
    pos_pr["pr"] = pos_pr["pr"].fillna(0.5)
    weighted_num = (pos_pr["amount"] * pos_pr["pr"]).groupby(pos_pr["user_id"]).sum()
    weighted_den = pos_pr.groupby("user_id")["amount"].sum()
    user_price_preference = (weighted_num / weighted_den).fillna(0.5)

    # ── user/item set lookups ───────────────────────────────────────────────
    user_items: dict = (
        pos.groupby("user_id")["item_id"].apply(set).to_dict()
    )
    user_l3_name_set: dict = (
        pos.groupby("user_id")["cat_l3_name"].apply(set).to_dict()
    )
    user_l3_code_items: dict = (
        pos.groupby("cat_l3_code")["item_id"].apply(set).to_dict()
    )

    # ── repurchase_need ─────────────────────────────────────────────────────
    d_max = pos["sale_date"].max()
    repurchase_need: dict = {}
    for (uid, l3c), grp in pos.groupby(["user_id", "cat_l3_code"])["sale_date"]:
        d = np.sort(grp.dt.normalize().unique())
        if len(d) >= 2:
            cycle = (
                np.diff(d).astype("timedelta64[D]").astype(float).mean()
            )
        else:
            cycle = 0.0
        last_day = pd.Timestamp(d[-1])
        repurchase_need[(uid, l3c)] = float(
            (d_max - last_day).days / (cycle + 1e-9)
        )

    # ── SVD graph embeddings ────────────────────────────────────────────────
    graph_embeddings: dict | None = None
    try:
        from scipy.sparse import csr_matrix
        from scipy.sparse.linalg import svds

        agg = (
            pos.groupby(["user_id", "item_id"])
            .agg(freq=("item_id", "size"), amt=("amount", "sum"), last=("sale_date", "max"))
            .reset_index()
        )
        dt_days = (d_max - agg["last"]).dt.days.values
        agg["w"] = (
            np.log1p(agg["freq"])
            + np.log1p(agg["amt"].clip(lower=0))
            + np.exp(-time_decay * dt_days)
        )
        users = agg["user_id"].unique()
        items = agg["item_id"].unique()
        uidx = {u: i for i, u in enumerate(users)}
        iidx = {it: j for j, it in enumerate(items)}
        rows = agg["user_id"].map(uidx).values
        cols = agg["item_id"].map(iidx).values
        M = csr_matrix(
            (agg["w"].values, (rows, cols)),
            shape=(len(users), len(items)),
        )
        k = min(svd_dim, min(M.shape) - 1)
        if k >= 1:
            U, S, Vt = svds(M, k=k)
            P = U * np.sqrt(S)
            Q = Vt.T * np.sqrt(S)
            graph_embeddings = {
                "P": P,
                "Q": Q,
                "uidx": uidx,
                "iidx": iidx,
                "iidx_inv": {j: it for it, j in iidx.items()},
            }
    except Exception:
        graph_embeddings = None

    # ── association scoring rules ───────────────────────────────────────────
    item_scoring_rules = _mine_scoring_rules(
        pos,
        "item_id",
        rule_min_support,
        rule_min_confidence,
        rule_min_lift,
        max_len=2,
    )
    l3_scoring_rules = _mine_scoring_rules(
        pos,
        "cat_l3_name",
        0.01,
        0.25,
        1.15,
        max_len=3,
    )

    return RetailRecommendationSignals(
        popularity=popularity,
        pop_rank_items=pop_rank_items,
        item_meta=item_meta,
        price_rank=price_rank,
        user_l3_preferences=user_l3_preferences,
        user_total_amount=user_total_amount,
        user_promo_sensitivity=user_promo_sensitivity,
        user_price_preference=user_price_preference,
        user_items=user_items,
        user_l3_name_set=user_l3_name_set,
        user_l3_code_items=user_l3_code_items,
        repurchase_need=repurchase_need,
        d_max=d_max,
        item_scoring_rules=item_scoring_rules,
        l3_scoring_rules=l3_scoring_rules,
        graph_embeddings=graph_embeddings,
    )
