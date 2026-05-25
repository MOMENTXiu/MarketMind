# -*- coding: utf-8 -*-
"""
阶段 4：商品关联模型（思路文档 §8、§14.2）
E1 FP-Growth 商品级 | E2 FP-Growth 小类级 | E3 高效用项集挖掘 HUIM | E4 层级规则融合
购物篮定义：B_{u,d} = 顾客 u 在日期 d 购买的（正向）商品/类目集合。

产出：
  output/csvs/association_rules_item.csv      商品级规则
  output/csvs/association_rules_category.csv  小类级 + 中类级规则
  output/csvs/high_utility_itemsets.csv       高效用商品组合（小类级）
  output/csvs/association_model_comparison.csv 四实验对比
  output/figures/13_商品共购网络.png
  output/figures/14_Top组合效用.png
  output/figures/as_规则指标分布.png
  output/pkls/association_rules.pkl
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules
from itertools import combinations
from collections import defaultdict

from config import load_clean, save_csv, set_style, savefig, save_pkl, PALETTE


def build_baskets(pos, key):
    """按 (user,date) 聚合为事务列表。key: 'item_id'/'cat_l3_name'/'cat_l2_name'"""
    g = pos.groupby(["user_id", "sale_date"])[key].apply(lambda s: sorted(set(s)))
    return [t for t in g.tolist() if len(t) >= 1]


def mine_rules(transactions, min_support, min_confidence, min_lift, max_len=3):
    te = TransactionEncoder()
    arr = te.fit_transform(transactions)
    dfb = pd.DataFrame(arr, columns=te.columns_)
    freq = fpgrowth(dfb, min_support=min_support, use_colnames=True, max_len=max_len)
    if freq.empty:
        return pd.DataFrame(), 0
    rules = association_rules(freq, metric="confidence", min_threshold=min_confidence)
    rules = rules[(rules["lift"] >= min_lift) & (rules["consequents"].apply(len) == 1)]
    rules = rules.sort_values(["lift", "confidence"], ascending=False)
    return rules, len(freq)


def rules_to_cn(rules, level):
    """转为中文表头输出表。"""
    if rules.empty:
        return pd.DataFrame()
    out = pd.DataFrame({
        "层级": level,
        "前项": rules["antecedents"].apply(lambda s: "+".join(sorted(s))),
        "后项": rules["consequents"].apply(lambda s: list(s)[0]),
        "支持度": rules["support"].round(4),
        "置信度": rules["confidence"].round(4),
        "提升度": rules["lift"].round(3),
    })
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 高效用项集挖掘 HUIM（小类级）
# 思路 §8.3： u(i,b)=qty*price; U(X)=Σ_b Σ_{i∈X} u(i,b)·I(X⊆b)
# 策略：以低支持度 FP-Growth 生成候选项集（含低频项），再计算真实效用并按 min_utility 过滤排序，
#       从而捕获“低频但高价值”的组合（传统支持度规则会漏掉）。
# ---------------------------------------------------------------------------
def mine_huim(pos, level="cat_l3_name", min_support=0.002, min_len=2, max_len=3, top=40):
    # 事务（集合）用于候选枚举
    baskets = pos.groupby(["user_id", "sale_date"])[level].apply(lambda s: sorted(set(s)))
    baskets = [b for b in baskets.tolist() if len(b) >= 2]
    n_tx = len(baskets)
    # 候选：低支持度频繁项集
    te = TransactionEncoder()
    arr = te.fit_transform(baskets)
    dfb = pd.DataFrame(arr, columns=te.columns_)
    freq = fpgrowth(dfb, min_support=min_support, use_colnames=True, max_len=max_len)
    freq = freq[freq["itemsets"].apply(len) >= min_len]
    if freq.empty:
        return pd.DataFrame()
    # 每个事务内各类目的效用（金额合计）
    util_tx = pos.groupby(["user_id", "sale_date", level])["amount"].sum()
    # 重建：每个事务 -> {类目: 效用}
    tx_index = pos.groupby(["user_id", "sale_date"])[level].apply(lambda s: set(s))
    tx_keys = [k for k, v in tx_index.items() if len(v) >= 2]
    tx_sets = [tx_index[k] for k in tx_keys]
    tx_util = []
    util_map = util_tx.to_dict()
    for k in tx_keys:
        u, d = k
        tx_util.append({c: util_map.get((u, d, c), 0.0) for c in tx_index[k]})

    rows = []
    total_util = sum(sum(d.values()) for d in tx_util)
    for itemset in freq["itemsets"]:
        items = set(itemset)
        U = 0.0
        cnt = 0
        for s, um in zip(tx_sets, tx_util):
            if items.issubset(s):
                U += sum(um[i] for i in items)
                cnt += 1
        if cnt == 0:
            continue
        rows.append(("+".join(sorted(items)), len(items), cnt, round(cnt / n_tx, 4),
                     round(U, 2), round(U / cnt, 2)))
    hui = pd.DataFrame(rows, columns=["组合", "项数", "出现篮数", "支持度", "总效用", "篮均效用"])
    # min_utility 阈值：总效用的中位数以上，并按总效用排序
    thr = hui["总效用"].quantile(0.5)
    hui = hui[hui["总效用"] >= thr].sort_values("总效用", ascending=False).head(top)
    hui["效用占比"] = (hui["总效用"] / total_util).round(4)
    return hui.reset_index(drop=True)


def main():
    set_style()
    df = load_clean()
    pos = df[df["is_return"] == 0].copy()
    results = {}

    # ---------- E1 商品级 ----------
    tx_item = build_baskets(pos, "item_id")
    rules_item, nfreq_i = mine_rules(tx_item, 0.003, 0.20, 1.10, max_len=2)
    item_cn = rules_to_cn(rules_item, "商品级")
    # 映射商品编码为「小类名(编码)」便于解读
    id2name = pos.drop_duplicates("item_id").set_index("item_id")["cat_l3_name"].to_dict()
    if not item_cn.empty:
        item_cn["前项类目"] = item_cn["前项"].apply(lambda s: "+".join(id2name.get(x, x) for x in s.split("+")))
        item_cn["后项类目"] = item_cn["后项"].map(id2name)
    save_csv(item_cn, "association_rules_item.csv")
    results["E1_商品级FP"] = dict(规则数=len(item_cn),
                                平均置信度=round(item_cn["置信度"].mean(), 4) if not item_cn.empty else 0,
                                平均提升度=round(item_cn["提升度"].mean(), 3) if not item_cn.empty else 0)

    # ---------- E2 小类级 ----------
    tx_l3 = build_baskets(pos, "cat_l3_name")
    rules_l3, nfreq_l3 = mine_rules(tx_l3, 0.01, 0.25, 1.15, max_len=3)
    l3_cn = rules_to_cn(rules_l3, "小类级")
    save_csv(l3_cn, "association_rules_category_l3.csv")
    results["E2_小类级FP"] = dict(规则数=len(l3_cn),
                                平均置信度=round(l3_cn["置信度"].mean(), 4) if not l3_cn.empty else 0,
                                平均提升度=round(l3_cn["提升度"].mean(), 3) if not l3_cn.empty else 0)

    # 中类级（用于经营分析）
    tx_l2 = build_baskets(pos, "cat_l2_name")
    rules_l2, _ = mine_rules(tx_l2, 0.015, 0.25, 1.15, max_len=2)
    l2_cn = rules_to_cn(rules_l2, "中类级")

    # 合并类目级规则输出
    cat_all = pd.concat([l3_cn, l2_cn], ignore_index=True)
    save_csv(cat_all, "association_rules_category.csv")

    # ---------- E3 HUIM ----------
    hui = mine_huim(pos, "cat_l3_name", min_support=0.002, min_len=2, max_len=3, top=40)
    save_csv(hui, "high_utility_itemsets.csv")
    results["E3_HUIM小类"] = dict(规则数=len(hui),
                                平均置信度=np.nan,
                                平均提升度=np.nan,
                                高效用组合数=len(hui),
                                Top组合效用=round(hui["总效用"].max(), 1) if not hui.empty else 0)

    # ---------- E4 层级融合 ----------
    # 商品级优先、小类级兜底、中类级解释；统计可用于营销组合的规则数（跨类目）
    results["E4_层级融合"] = dict(商品级=len(item_cn), 小类级=len(l3_cn),
                               中类级=len(l2_cn), 高效用组合=len(hui),
                               合计可用规则=len(item_cn) + len(l3_cn) + len(l2_cn))

    comp = pd.DataFrame(results).T
    save_csv(comp.reset_index().rename(columns={"index": "实验"}), "association_model_comparison.csv")
    print("=== 关联规则实验汇总 ===")
    print("商品级规则:", len(item_cn), "| 小类级:", len(l3_cn), "| 中类级:", len(l2_cn),
          "| 高效用组合:", len(hui))
    if not l3_cn.empty:
        print("\n小类级 Top5 规则:")
        print(l3_cn.head(5).to_string(index=False))
    if not hui.empty:
        print("\nHUIM Top5 高效用组合:")
        print(hui.head(5).to_string(index=False))

    save_pkl({"rules_item": item_cn, "rules_l3": l3_cn, "rules_l2": l2_cn, "huim": hui},
             "association_rules.pkl")

    _plots(l3_cn, hui)
    return item_cn, cat_all, hui, comp


def _plots(l3_cn, hui):
    # 图13：小类共购网络（Top 规则）
    if not l3_cn.empty:
        top = l3_cn.head(35)
        G = nx.DiGraph()
        for _, r in top.iterrows():
            for a in r["前项"].split("+"):
                G.add_edge(a, r["后项"], weight=r["提升度"])
        fig, ax = plt.subplots(figsize=(10, 8))
        pos_ = nx.spring_layout(G, k=0.7, seed=42)
        deg = dict(G.degree())
        sizes = [300 + 250 * deg[n] for n in G.nodes()]
        weights = [G[u][v]["weight"] for u, v in G.edges()]
        nx.draw_networkx_nodes(G, pos_, node_size=sizes, node_color=PALETTE[0],
                               alpha=0.85, ax=ax, edgecolors="white")
        nx.draw_networkx_edges(G, pos_, width=[0.6 + 0.5 * w for w in weights],
                               edge_color="#888888", alpha=0.5, ax=ax,
                               arrowsize=10, connectionstyle="arc3,rad=0.08")
        nx.draw_networkx_labels(G, pos_, font_size=8,
                                font_family="Microsoft YaHei", ax=ax)
        ax.axis("off")
        savefig(fig, "13_商品共购网络.png")

    # 图14：Top 组合效用（瀑布/条形）
    if not hui.empty:
        top = hui.head(15)
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(top["组合"][::-1], top["总效用"][::-1], color=PALETTE[5],
                edgecolor="white")
        ax.set_xlabel("组合总效用 (元)")
        savefig(fig, "14_Top组合效用.png")

    # 规则指标分布（小类级 置信度 vs 提升度 散点，气泡=支持度）
    if not l3_cn.empty:
        fig, ax = plt.subplots(figsize=(8, 5.5))
        sc = ax.scatter(l3_cn["置信度"], l3_cn["提升度"],
                        s=l3_cn["支持度"] * 4000 + 20, c=l3_cn["提升度"],
                        cmap="YlOrRd", alpha=0.7, edgecolors="#666666", linewidths=0.5)
        ax.axhline(1.0, color="#999999", ls="--", lw=1)
        ax.set_xlabel("置信度"); ax.set_ylabel("提升度")
        cb = fig.colorbar(sc, ax=ax); cb.set_label("提升度")
        savefig(fig, "as_规则指标分布.png")


if __name__ == "__main__":
    main()
