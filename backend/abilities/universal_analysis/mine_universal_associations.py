"""Mine universal association rules (FP-Growth) with basket-structure runtime checks."""

from __future__ import annotations

from typing import Any

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

from backend.abilities.universal_analysis.common import positive


def _baskets(pos: pd.DataFrame, key: str) -> list[list[str]]:
    g = pos.groupby("order_id")[key].apply(lambda s: sorted(set(s)))
    return [t for t in g.tolist() if len(t) >= 1]


def _mine(
    tx: list[list[str]], sup: float, conf: float, lift: float, maxlen: int = 3
) -> pd.DataFrame:
    te = TransactionEncoder()
    arr = te.fit_transform(tx)
    dfb = pd.DataFrame(arr, columns=te.columns_)
    fq = fpgrowth(dfb, min_support=sup, use_colnames=True, max_len=maxlen)
    if fq.empty:
        return pd.DataFrame()
    r = association_rules(fq, metric="confidence", min_threshold=conf)
    r = r[(r["lift"] >= lift) & (r["consequents"].apply(len) == 1)]
    return r.sort_values("lift", ascending=False)


def mine_universal_associations(df: pd.DataFrame, _cap: dict[str, Any]) -> dict[str, Any]:
    """Return association result dict with rules and HUIM."""
    if "order_id" not in df.columns:
        return {"status": "skipped", "reason": "无 order_id"}
    pos = positive(df)
    bs = pos.groupby("order_id").size()
    avg_basket = bs.mean()
    multi = (bs >= 2).mean()
    if avg_basket < 1.5 or multi < 0.1:
        return {
            "status": "skipped",
            "reason": f"篮均{avg_basket:.2f}、多品篮{multi:.1%}，无共购结构，关联规则不适用",
        }

    level = (
        "cat_l3_name"
        if "cat_l3_name" in pos.columns
        else "cat_l1_name"
        if "cat_l1_name" in pos.columns
        else "item_id"
    )
    tx = _baskets(pos, level)
    rules = _mine(tx, 0.01, 0.2, 1.1)

    cn = pd.DataFrame()
    if not rules.empty:
        cn = pd.DataFrame(
            {
                "前项": rules["antecedents"].apply(lambda s: "+".join(sorted(s))),
                "后项": rules["consequents"].apply(lambda s: list(s)[0]),
                "支持度": rules["support"].round(4),
                "置信度": rules["confidence"].round(4),
                "提升度": rules["lift"].round(3),
            }
        ).reset_index(drop=True)

    hui = pd.DataFrame()
    if "amount" in pos.columns and not cn.empty:
        util = pos.groupby(["order_id", level])["amount"].sum()
        umap = util.to_dict()
        bk = pos.groupby("order_id")[level].apply(lambda s: set(s))
        bk = bk[bk.apply(len) >= 2]
        rows = []
        for _, r in cn.head(30).iterrows():
            items = set(r["前项"].split("+") + [r["后项"]])
            U = cnt = 0
            for oid, st in bk.items():
                if items <= st:
                    U += sum(umap.get((oid, it), 0) for it in items)
                    cnt += 1
            if cnt:
                rows.append(
                    {
                        "组合": "+".join(sorted(items)),
                        "出现篮数": cnt,
                        "总效用": round(U, 1),
                        "篮均效用": round(U / cnt, 2),
                    }
                )
        hui = (
            pd.DataFrame(rows)
            .drop_duplicates("组合")
            .sort_values("总效用", ascending=False)
            .head(15)
        )

    return {
        "status": "ok",
        "level": level,
        "avg_basket": round(avg_basket, 2),
        "n_rules": len(cn),
        "avg_lift": round(cn["提升度"].mean(), 3) if not cn.empty else 0,
        "top_rule": (cn.iloc[0]["前项"] + "→" + cn.iloc[0]["后项"]) if not cn.empty else None,
        "rules": cn.to_dict("records"),
        "huim": hui.to_dict("records"),
    }
