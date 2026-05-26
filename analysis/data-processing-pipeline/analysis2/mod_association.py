# -*- coding: utf-8 -*-
"""普适分析模块 3：关联规则（FP-Growth）。
运行时可行性校验：需 order_id + 多品篮（篮均>=1.5），否则跳过并说明。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules
from config_3 import savefig, save_csv, positive, PALETTE


def _baskets(pos, key):
    g = pos.groupby("order_id")[key].apply(lambda s: sorted(set(s)))
    return [t for t in g.tolist() if len(t) >= 1]


def _mine(tx, sup, conf, lift, maxlen=3):
    te = TransactionEncoder(); arr = te.fit_transform(tx)
    dfb = pd.DataFrame(arr, columns=te.columns_)
    fq = fpgrowth(dfb, min_support=sup, use_colnames=True, max_len=maxlen)
    if fq.empty:
        return pd.DataFrame()
    r = association_rules(fq, metric="confidence", min_threshold=conf)
    r = r[(r["lift"] >= lift) & (r["consequents"].apply(len) == 1)]
    return r.sort_values("lift", ascending=False)


def run(df, dataset, cap):
    if "order_id" not in df.columns:
        return {"status": "skipped", "reason": "无 order_id"}
    pos = positive(df)
    bs = pos.groupby("order_id").size()
    avg_basket = bs.mean(); multi = (bs >= 2).mean()
    # 运行时可行性校验
    if avg_basket < 1.5 or multi < 0.1:
        return {"status": "skipped",
                "reason": f"篮均{avg_basket:.2f}、多品篮{multi:.1%}，无共购结构，关联规则不适用"}

    # 选择项粒度：优先小类，其次大类，再次商品
    level = ("cat_l3_name" if "cat_l3_name" in pos.columns else
             "cat_l1_name" if "cat_l1_name" in pos.columns else "item_id")
    tx = _baskets(pos, level)
    rules = _mine(tx, 0.01, 0.2, 1.1)
    cn = pd.DataFrame()
    if not rules.empty:
        cn = pd.DataFrame({
            "前项": rules["antecedents"].apply(lambda s: "+".join(sorted(s))),
            "后项": rules["consequents"].apply(lambda s: list(s)[0]),
            "支持度": rules["support"].round(4), "置信度": rules["confidence"].round(4),
            "提升度": rules["lift"].round(3)}).reset_index(drop=True)
    save_csv(cn, dataset, "association_rules.csv")

    # 高效用组合（HUIM 简化：频繁项集按金额效用排序）
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
                    U += sum(umap.get((oid, it), 0) for it in items); cnt += 1
            if cnt:
                rows.append({"组合": "+".join(sorted(items)), "出现篮数": cnt,
                             "总效用": round(U, 1), "篮均效用": round(U / cnt, 2)})
        hui = pd.DataFrame(rows).drop_duplicates("组合").sort_values("总效用", ascending=False).head(15)
        save_csv(hui, dataset, "association_huim.csv")

    _plots(cn, level, dataset)
    return {"status": "ok", "level": level, "avg_basket": round(avg_basket, 2),
            "n_rules": len(cn),
            "avg_lift": round(cn["提升度"].mean(), 3) if not cn.empty else 0,
            "top_rule": (cn.iloc[0]["前项"] + "→" + cn.iloc[0]["后项"]) if not cn.empty else None}


def _plots(cn, level, dataset):
    if cn.empty:
        return
    # 共购网络
    top = cn.head(30)
    G = nx.DiGraph()
    for _, r in top.iterrows():
        for a in r["前项"].split("+"):
            G.add_edge(a, r["后项"], weight=r["提升度"])
    if G.number_of_edges() > 0:
        fig, ax = plt.subplots(figsize=(9, 7.5))
        posg = nx.spring_layout(G, k=0.7, seed=42)
        deg = dict(G.degree())
        nx.draw_networkx_nodes(G, posg, node_size=[200 + 180 * deg[n] for n in G.nodes()],
                               node_color=PALETTE[0], alpha=0.85, ax=ax, edgecolors="white")
        nx.draw_networkx_edges(G, posg, edge_color="#999", alpha=0.5, ax=ax, arrowsize=9,
                               connectionstyle="arc3,rad=0.08")
        nx.draw_networkx_labels(G, posg, font_size=8, font_family="Microsoft YaHei", ax=ax)
        ax.axis("off")
        savefig(fig, dataset, "association_共购网络.png")
    # 指标气泡
    fig, ax = plt.subplots(figsize=(8, 5.5))
    sc = ax.scatter(cn["置信度"], cn["提升度"], s=cn["支持度"] * 3000 + 20,
                    c=cn["提升度"], cmap="YlOrRd", alpha=0.7, edgecolors="#666", linewidths=0.5)
    ax.axhline(1, color="#999", ls="--", lw=1)
    ax.set_xlabel("置信度"); ax.set_ylabel("提升度"); fig.colorbar(sc, ax=ax, label="提升度")
    savefig(fig, dataset, "association_指标分布.png")
