# -*- coding: utf-8 -*-
"""
阶段 5：消费者侧推荐（思路文档 §9、§10、§13.1、§14.3）
召回：E1全局热门 | E2类目偏好 | E3关联规则 | E4二部图嵌入(SVD/LightGCN同源) | E5复购周期
融合：E6 CRITIC-TOPSIS（候选指标：6类召回得分 + 商品热度 + 促销适配 + 价格匹配）
评估：时间切分（1–3月训练 / 4月验证），Precision/Recall/HitRate/NDCG@K + Coverage/Diversity/PromoMatchRate。
所有召回信号仅由训练期数据构造，严格防泄漏。

产出：
  output/csvs/user_recommendations.csv          Top-K 推荐 + 理由 + 策略
  output/csvs/recommendation_evaluation.csv      E1-E6 评估对比
  output/csvs/critic_weights_reco.csv            推荐融合 CRITIC 权重
  output/figures/17_推荐命中率对比.png
  output/figures/18_CRITIC指标权重.png
  output/figures/19_TOPSIS贴近度分布.png
  output/figures/15_推荐来源占比.png
  output/pkls/recommendation_artifacts.pkl
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules

from config import (load_clean, save_csv, set_style, savefig, save_pkl,
                    critic_weights, topsis, PALETTE, CSV_DIR)

SPLIT_DATE = pd.Timestamp("2025-04-01")
K_LIST = [5, 10]
TIME_DECAY = 0.02   # 边权时间衰减 λ


# ===========================================================================
# 训练期信号构造（防泄漏）
# ===========================================================================
def build_train_signals(train):
    sig = {}
    D_max = train["sale_date"].max()

    # 商品热度（训练期 TOPSIS: 金额/数量/购买人数, log 压缩）
    pg = train.groupby("item_id").agg(amt=("amount", "sum"), qty=("quantity", "sum"),
                                      buyers=("user_id", "nunique"))
    X = np.log1p(pg[["amt", "qty", "buyers"]].clip(lower=0).values)
    w, _ = critic_weights(X)
    pop, _ = topsis(X, w)
    pg["popularity"] = pop
    sig["popularity"] = pg["popularity"]
    sig["pop_rank_items"] = pg["popularity"].sort_values(ascending=False)

    # 商品->类目映射
    item_meta = train.drop_duplicates("item_id").set_index("item_id")[
        ["cat_l1_name", "cat_l2_name", "cat_l3_name", "cat_l3_code", "is_promo"]]
    # 商品是否促销（训练期促销笔数占比）
    item_meta["promo_rate"] = train.groupby("item_id")["is_promo"].mean()
    sig["item_meta"] = item_meta

    # 商品在小类内价格分位
    ip = train.groupby(["cat_l3_code", "item_id"])["unit_price"].mean().reset_index()
    ip["price_rank"] = ip.groupby("cat_l3_code")["unit_price"].rank(pct=True)
    sig["price_rank"] = ip.set_index("item_id")["price_rank"]

    # 用户类目偏好（L3 金额占比）
    u_l3 = train.groupby(["user_id", "cat_l3_code"])["amount"].sum()
    u_tot = train.groupby("user_id")["amount"].sum()
    sig["u_l3_pref"] = (u_l3 / u_tot).rename("pref")           # MultiIndex (user,l3)
    sig["u_total_amt"] = u_tot

    # 用户促销敏感度（训练期促销金额占比）
    promo_amt = train[train["is_promo"] == 1].groupby("user_id")["amount"].sum()
    sig["promo_sens"] = (promo_amt / u_tot).fillna(0)

    # 用户偏好价格分位（金额加权）
    tr = train.merge(sig["price_rank"].rename("pr"), left_on="item_id", right_index=True, how="left")
    tr["pr"] = tr["pr"].fillna(0.5)
    sig["price_pref"] = (tr.assign(w=tr["amount"] * tr["pr"]).groupby("user_id")["w"].sum()
                         / u_tot).fillna(0.5)

    # 用户历史购买商品/类目集合
    sig["u_items"] = train.groupby("user_id")["item_id"].apply(set)
    sig["u_l3set"] = train.groupby("user_id")["cat_l3_name"].apply(set)
    sig["u_l3code_items"] = train.groupby("cat_l3_code")["item_id"].apply(lambda s: set(s))

    # 复购周期 Need（user,l3）
    need = {}
    grp = train.groupby(["user_id", "cat_l3_code"])["sale_date"]
    for (u, c), dates in grp:
        d = np.sort(dates.dt.normalize().unique())
        if len(d) >= 2:
            cycle = np.diff(d).astype("timedelta64[D]").astype(float).mean()
            need[(u, c)] = (D_max - pd.Timestamp(d[-1])).days / (cycle + 1e-9)
    sig["need"] = need
    sig["D_max"] = D_max
    return sig


# ===========================================================================
# 关联规则（训练期，L3 + item）
# ===========================================================================
def mine_train_rules(train):
    pos = train
    def baskets(key):
        g = pos.groupby(["user_id", "sale_date"])[key].apply(lambda s: sorted(set(s)))
        return [t for t in g.tolist() if len(t) >= 2]
    def rules_of(tx, sup, conf, lift, maxlen):
        te = TransactionEncoder(); arr = te.fit_transform(tx)
        dfb = pd.DataFrame(arr, columns=te.columns_)
        fq = fpgrowth(dfb, min_support=sup, use_colnames=True, max_len=maxlen)
        if fq.empty:
            return {}
        r = association_rules(fq, metric="confidence", min_threshold=conf)
        r = r[(r["lift"] >= lift) & (r["consequents"].apply(len) == 1)]
        d = {}
        for _, row in r.iterrows():
            ante = frozenset(row["antecedents"]); cons = list(row["consequents"])[0]
            d.setdefault(ante, []).append((cons, row["confidence"] * row["lift"]))
        return d
    return rules_of(baskets("item_id"), 0.003, 0.2, 1.1, 2), \
           rules_of(baskets("cat_l3_name"), 0.01, 0.25, 1.15, 3)


# ===========================================================================
# 二部图嵌入（加权用户-商品矩阵截断 SVD；LightGCN 同源的低秩图嵌入）
# 边权 w=log(1+freq)+log(1+amount)+exp(-λΔt)（思路 §9.2.1）
# ===========================================================================
def build_graph_embedding(train, dim=48):
    D_max = train["sale_date"].max()
    agg = train.groupby(["user_id", "item_id"]).agg(
        freq=("item_id", "size"), amt=("amount", "sum"),
        last=("sale_date", "max")).reset_index()
    dt = (D_max - agg["last"]).dt.days.values
    agg["w"] = np.log1p(agg["freq"]) + np.log1p(agg["amt"].clip(lower=0)) + np.exp(-TIME_DECAY * dt)
    users = agg["user_id"].unique(); items = agg["item_id"].unique()
    uidx = {u: i for i, u in enumerate(users)}; iidx = {it: j for j, it in enumerate(items)}
    rows = agg["user_id"].map(uidx).values; cols = agg["item_id"].map(iidx).values
    M = csr_matrix((agg["w"].values, (rows, cols)), shape=(len(users), len(items)))
    k = min(dim, min(M.shape) - 1)
    U, S, Vt = svds(M, k=k)
    P = U * np.sqrt(S); Q = (Vt.T) * np.sqrt(S)
    return {"P": P, "Q": Q, "uidx": uidx, "iidx": iidx,
            "items": items, "iidx_inv": {j: it for it, j in iidx.items()}}


# ===========================================================================
# 候选召回 + 各信号打分
# ===========================================================================
def recommend_user(u, sig, rules_item, rules_l3, gemb, topN_pool=250):
    cand = {}  # item -> dict of signal scores
    item_meta = sig["item_meta"]
    pop = sig["popularity"]
    u_items = sig["u_items"].get(u, set())

    def ensure(i):
        if i not in cand:
            cand[i] = dict(graph=0.0, rule=0.0, cat=0.0, cycle=0.0, promo=0.0, price=0.0)

    # --- E4 图嵌入召回 ---
    if u in gemb["uidx"]:
        pu = gemb["P"][gemb["uidx"][u]]
        scores = gemb["Q"] @ pu
        topg = np.argsort(-scores)[:120]
        smin, smax = scores[topg].min(), scores[topg].max()
        for j in topg:
            i = gemb["iidx_inv"][j]
            ensure(i)
            cand[i]["graph"] = float((scores[j] - smin) / (smax - smin + 1e-9))

    # --- E2 类目偏好召回 ---
    prefs = sig["u_l3_pref"].get(u) if hasattr(sig["u_l3_pref"], "get") else None
    try:
        upref = sig["u_l3_pref"].loc[u]    # Series indexed by l3code
        upref = upref.sort_values(ascending=False).head(8)
        for l3c, p in upref.items():
            items_c = sig["u_l3code_items"].get(l3c, set())
            # 该小类下训练期热门商品
            sub = pop[pop.index.isin(items_c)].sort_values(ascending=False).head(20)
            for i, pv in sub.items():
                ensure(i); cand[i]["cat"] = max(cand[i]["cat"], float(p) * float(pv))
    except (KeyError, AttributeError):
        pass

    # --- E3 关联规则召回（基于历史商品/小类） ---
    for i in list(u_items)[:60]:
        for ante, cons_list in rules_item.items():
            if ante <= u_items:
                for cons, sc in cons_list:
                    ensure(cons); cand[cons]["rule"] = max(cand[cons]["rule"], sc)
                break
    u_l3set = sig["u_l3set"].get(u, set())
    for ante, cons_list in rules_l3.items():
        if ante <= u_l3set:
            for cons_l3, sc in cons_list:
                # 推该小类训练期热门商品
                items_c = set(item_meta.index[item_meta["cat_l3_name"] == cons_l3])
                sub = pop[pop.index.isin(items_c)].sort_values(ascending=False).head(8)
                for i, pv in sub.items():
                    ensure(i); cand[i]["rule"] = max(cand[i]["rule"], sc * 0.3)

    # --- E5 复购周期召回 ---
    for (uu, l3c), need in sig["need"].items():
        if uu != u:
            continue
        score = min(need, 2.0) / 2.0   # 归一到[0,1]，Need≈1最紧迫
        items_c = sig["u_l3code_items"].get(l3c, set())
        sub = pop[pop.index.isin(items_c)].sort_values(ascending=False).head(10)
        for i, pv in sub.items():
            ensure(i); cand[i]["cycle"] = max(cand[i]["cycle"], score)

    if not cand:
        # 冷启动：全局热门
        for i in sig["pop_rank_items"].head(topN_pool).index:
            ensure(i)

    # --- 促销适配 & 价格匹配（对所有候选）---
    psens = sig["promo_sens"].get(u, 0.0)
    ppref = sig["price_pref"].get(u, 0.5)
    for i in cand:
        pr = item_meta["promo_rate"].get(i, 0.0)
        cand[i]["promo"] = psens * pr
        prk = sig["price_rank"].get(i, 0.5)
        cand[i]["price"] = 1.0 - abs(ppref - prk)
        cand[i]["pop"] = float(pop.get(i, 0.0))

    return cand


# ===========================================================================
# 各模型 Top-K
# ===========================================================================
def rank_single(cand, signal):
    """单信号排序（E1-E5 baseline）。"""
    items = [i for i in cand if cand[i].get(signal, 0) > 0]
    items.sort(key=lambda i: cand[i][signal], reverse=True)
    return items


FUSE_COLS = ["graph", "rule", "cat", "cycle", "promo", "price", "pop"]


def rank_topsis(cand, reliability=None):
    """E6 CRITIC-TOPSIS 融合排序。
    权重 = CRITIC信息量 × 信号预测可靠度(由训练内部时间切分得到)，再归一化。
    既保持「不人工拍权重」，又让无关高方差信号(如价格)被自动压低、强预测信号被提升。
    返回 (排序items, 贴近度, 最终权重)。"""
    items = list(cand.keys())
    X = np.array([[cand[i][c] for c in FUSE_COLS] for i in items], float)
    if X.shape[0] < 2 or np.allclose(X.std(axis=0).sum(), 0):
        order = sorted(items, key=lambda i: cand[i]["pop"], reverse=True)
        return order, np.zeros(len(items)), None
    w_critic, _ = critic_weights(X)
    if reliability is not None:
        rel = np.array([reliability.get(c, 1e-3) for c in FUSE_COLS], float)
        w = w_critic * rel
        w = w / (w.sum() + 1e-12)
    else:
        w = w_critic
    clo, _ = topsis(X, w)
    order = [items[j] for j in np.argsort(-clo)]
    return order, clo, dict(zip(FUSE_COLS, w))


# ===========================================================================
# 评估指标
# ===========================================================================
def ndcg_at_k(rec, truth, k):
    dcg = sum((1.0 / np.log2(r + 2)) for r, i in enumerate(rec[:k]) if i in truth)
    idcg = sum((1.0 / np.log2(r + 2)) for r in range(min(len(truth), k)))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate(rec_dict, truth_dict, all_items, k, promo_items=None, cat_map=None):
    P = R = H = N = 0.0; n = 0
    rec_union = set(); div_sum = 0.0; promo_hit = 0.0; promo_tot = 0
    for u, rec in rec_dict.items():
        truth = truth_dict.get(u, set())
        if not truth:
            continue
        n += 1
        topk = rec[:k]
        hit = len(set(topk) & truth)
        P += hit / k
        R += hit / len(truth)
        H += 1.0 if hit > 0 else 0.0
        N += ndcg_at_k(rec, truth, k)
        rec_union |= set(topk)
        if cat_map is not None and topk:
            div_sum += len(set(cat_map.get(i, i) for i in topk)) / len(topk)
        if promo_items is not None and topk:
            pm = sum(1 for i in topk if i in promo_items)
            promo_hit += pm / len(topk)
            promo_tot += 1
    if n == 0:
        return {}
    return {
        f"Precision@{k}": P / n, f"Recall@{k}": R / n, f"HitRate@{k}": H / n,
        f"NDCG@{k}": N / n, f"Coverage@{k}": len(rec_union) / max(len(all_items), 1),
        f"Diversity@{k}": (div_sum / n) if cat_map is not None else np.nan,
        f"PromoMatch@{k}": (promo_hit / promo_tot) if promo_tot else 0.0,
    }


SIGNALS = ["graph", "rule", "cat", "cycle", "promo", "price"]


def compute_signal_reliability(pos, inner_split="2025-03-01"):
    """训练集内部时间切分（<3月 训练 / 3月 验证），评估每个召回信号的标准化预测可靠度。
    返回 {signal: reliability∈[~0,1]}，用于校准融合权重（数据驱动，非人工设定）。"""
    isp = pd.Timestamp(inner_split)
    itrain = pos[pos["sale_date"] < isp].copy()
    ival = pos[(pos["sale_date"] >= isp) & (pos["sale_date"] < SPLIT_DATE)].copy()
    if itrain.empty or ival.empty:
        return {s: 1.0 for s in FUSE_COLS}
    sig = build_train_signals(itrain)
    ri, rl = mine_train_rules(itrain)
    ge = build_graph_embedding(itrain)
    truth = ival.groupby("user_id")["item_id"].apply(set).to_dict()
    tr_users = set(itrain["user_id"].unique())
    users = [u for u in truth if u in tr_users]
    # 采样以控速
    rng = np.random.default_rng(0)
    if len(users) > 500:
        users = list(rng.choice(users, 500, replace=False))
    recs = {s: {} for s in SIGNALS}
    for u in users:
        cand = recommend_user(u, sig, ri, rl, ge)
        if not cand:
            continue
        for s in SIGNALS:
            recs[s][u] = rank_single(cand, s)
    rel = {}
    for s in SIGNALS:
        m = evaluate(recs[s], truth, list(sig["popularity"].index), 10)
        rel[s] = m.get("Recall@10", 0.0) + m.get("Precision@10", 0.0)
    rel["pop"] = max(rel.values()) if rel else 1.0   # 热度作为稳健兜底，给最高可靠度
    mx = max(rel.values()) + 1e-9
    rel = {k: v / mx for k, v in rel.items()}          # 归一到[0,1]
    print("信号可靠度(内部验证):", {k: round(v, 3) for k, v in rel.items()})
    return rel


def main():
    set_style()
    df = load_clean()
    pos = df[df["is_return"] == 0].copy()
    train = pos[pos["sale_date"] < SPLIT_DATE].copy()
    test = pos[pos["sale_date"] >= SPLIT_DATE].copy()
    print(f"训练 {len(train)} 行 / 验证 {len(test)} 行")

    reliability = compute_signal_reliability(pos)

    sig = build_train_signals(train)
    rules_item, rules_l3 = mine_train_rules(train)
    print(f"训练期规则: 商品级 {sum(len(v) for v in rules_item.values())} / 小类级 {sum(len(v) for v in rules_l3.values())}")
    gemb = build_graph_embedding(train)

    # 评估用户：训练有历史 且 4月有购买
    test_truth_item = test.groupby("user_id")["item_id"].apply(set).to_dict()
    test_truth_l3 = test.groupby("user_id")["cat_l3_name"].apply(set).to_dict()
    train_users = set(train["user_id"].unique())
    eval_users = [u for u in test_truth_item if u in train_users]
    print(f"评估用户数: {len(eval_users)}")

    all_items = list(sig["popularity"].index)
    promo_items = set(sig["item_meta"].index[sig["item_meta"]["promo_rate"] > 0.5])
    l3_of = sig["item_meta"]["cat_l3_name"].to_dict()

    # 为每个评估用户生成候选与各模型排序
    model_recs = {m: {} for m in ["E1_全局热门", "E2_类目偏好", "E3_关联规则",
                                  "E4_图嵌入", "E5_复购周期", "E6_CRITIC_TOPSIS"]}
    topsis_scores_all = []
    critic_w_acc = []
    src_counter = dict(graph=0, rule=0, cat=0, cycle=0, promo=0, price=0)
    rec_records = []

    pop_global = sig["pop_rank_items"].head(50).index.tolist()

    for u in eval_users:
        cand = recommend_user(u, sig, rules_item, rules_l3, gemb)
        if not cand:
            continue
        model_recs["E1_全局热门"][u] = pop_global
        model_recs["E2_类目偏好"][u] = rank_single(cand, "cat") or pop_global
        model_recs["E3_关联规则"][u] = rank_single(cand, "rule") or pop_global
        model_recs["E4_图嵌入"][u] = rank_single(cand, "graph") or pop_global
        model_recs["E5_复购周期"][u] = rank_single(cand, "cycle") or pop_global
        order, clo, w = rank_topsis(cand, reliability)
        model_recs["E6_CRITIC_TOPSIS"][u] = order
        if w:
            critic_w_acc.append(w)
            if len(clo):
                topsis_scores_all.extend(clo.tolist())
        # 记录 Top10 推荐明细（含理由）——按【加权贡献】归因主要来源，反映真正驱动排序的信号
        wmap = w if w else {s: 1.0 for s in SIGNALS}
        for rank, i in enumerate(order[:10], 1):
            c = cand[i]
            src = max(SIGNALS, key=lambda s: c[s] * wmap.get(s, 0.0))
            src_counter[src] += 1
            rec_records.append({
                "user_id": u, "rank": rank, "item_id": i,
                "cat_l1": sig["item_meta"]["cat_l1_name"].get(i, ""),
                "cat_l3": l3_of.get(i, ""),
                "score": round(float(clo[order.index(i)]), 4) if len(clo) else 0,
                "主要来源": {"graph": "图推荐", "rule": "关联规则", "cat": "类目偏好",
                          "cycle": "复购周期", "promo": "促销适配", "price": "价格匹配"}[src],
                "reason": _reason(src, c, sig, u, i, l3_of),
            })

    # 评估（商品级 + 小类级）
    rows = []
    l3_recs = {m: {u: [l3_of.get(i, "") for i in rec] for u, rec in d.items()}
               for m, d in model_recs.items()}
    all_l3 = list(set(l3_of.values()))
    for m in model_recs:
        for k in K_LIST:
            r_item = evaluate(model_recs[m], test_truth_item, all_items, k, promo_items, cat_map=l3_of)
            r_l3 = evaluate(l3_recs[m], test_truth_l3, all_l3, k)
            row = {"模型": m, "K": k}
            row.update({f"商品_{kk.split('@')[0]}": round(vv, 4) for kk, vv in r_item.items()})
            row.update({f"小类_{kk.split('@')[0]}": round(vv, 4)
                        for kk, vv in r_l3.items() if "Promo" not in kk and "Coverage" not in kk and "Diversity" not in kk})
            rows.append(row)
    ev = pd.DataFrame(rows)
    save_csv(ev, "recommendation_evaluation.csv")
    print("\n=== 推荐评估（节选 K=10）===")
    print(ev[ev["K"] == 10][["模型", "商品_Precision", "商品_Recall", "商品_HitRate",
                             "商品_NDCG", "小类_HitRate", "商品_Coverage"]].to_string(index=False))

    # 推荐明细
    rec_df = pd.DataFrame(rec_records)
    save_csv(rec_df, "user_recommendations.csv")

    # CRITIC 权重（均值）
    if critic_w_acc:
        wdf = pd.DataFrame(critic_w_acc).mean().reset_index()
        wdf.columns = ["推荐指标", "CRITIC权重"]
        name_map = {"graph": "图嵌入", "rule": "关联规则", "cat": "类目偏好",
                    "cycle": "复购周期", "promo": "促销适配", "price": "价格匹配", "pop": "商品热度"}
        wdf["推荐指标"] = wdf["推荐指标"].map(name_map)
        wdf["CRITIC权重"] = wdf["CRITIC权重"].round(4)
        save_csv(wdf, "critic_weights_reco.csv")
    else:
        wdf = pd.DataFrame()

    save_pkl({"sig_keys": list(sig.keys()), "rules_item_n": len(rules_item),
              "graph_dim": gemb["P"].shape}, "recommendation_artifacts.pkl")

    _plots(ev, wdf, topsis_scores_all, src_counter)
    return ev, rec_df


def _reason(src, c, sig, u, i, l3_of):
    l3 = l3_of.get(i, "该类目")
    return {
        "graph": "与你购买行为相似的顾客也常购买该商品",
        "rule": f"与你近期购买商品强关联（{l3}）",
        "cat": f"你长期偏好「{l3}」类目",
        "cycle": f"你可能接近「{l3}」的复购周期",
        "promo": "你对促销较敏感，该商品当前促销适配度高",
        "price": "该商品符合你的常购价格带",
    }[src]


def _plots(ev, wdf, topsis_scores, src_counter):
    # 图17：推荐命中率对比（K=10，商品级与小类级 HitRate）
    e10 = ev[ev["K"] == 10]
    x = np.arange(len(e10)); wd = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - wd/2, e10["商品_HitRate"], wd, label="商品级 HitRate@10",
           color=PALETTE[0], edgecolor="white")
    ax.bar(x + wd/2, e10["小类_HitRate"], wd, label="小类级 HitRate@10",
           color=PALETTE[1], edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(e10["模型"], rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("HitRate@10"); ax.legend()
    savefig(fig, "17_推荐命中率对比.png")

    # 图18：CRITIC 指标权重
    if not wdf.empty:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        wsort = wdf.sort_values("CRITIC权重", ascending=True)
        ax.barh(wsort["推荐指标"], wsort["CRITIC权重"], color=PALETTE[4], edgecolor="white")
        ax.set_xlabel("CRITIC 权重")
        savefig(fig, "18_CRITIC指标权重.png")

    # 图19：TOPSIS 贴近度分布
    if topsis_scores:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.hist(topsis_scores, bins=40, color=PALETTE[2], alpha=0.8, edgecolor="white")
        ax.set_xlabel("TOPSIS 贴近度 C_i"); ax.set_ylabel("候选商品数")
        savefig(fig, "19_TOPSIS贴近度分布.png")

    # 图15：推荐来源占比（环形）
    labels_map = {"graph": "图推荐", "rule": "关联规则", "cat": "类目偏好",
                  "cycle": "复购周期", "promo": "促销适配", "price": "价格匹配"}
    items = [(labels_map[k], v) for k, v in src_counter.items() if v > 0]
    if items:
        labs, vals = zip(*items)
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.pie(vals, labels=labs, autopct="%1.1f%%", startangle=90, counterclock=False,
               colors=PALETTE[:len(vals)], wedgeprops=dict(width=0.42, edgecolor="white"),
               pctdistance=0.78, textprops={"fontsize": 10})
        ax.set(aspect="equal")
        savefig(fig, "15_推荐来源占比.png")


if __name__ == "__main__":
    main()
