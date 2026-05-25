# -*- coding: utf-8 -*-
"""
阶段 2：特征工程（顾客画像 + 商品画像）
依据思路文档 §5（顾客画像）与 §6（商品画像）。

产出：
    output/csvs/customer_profile.csv     顾客画像（建模主表）
    output/csvs/product_profile.csv      商品画像
    output/csvs/repurchase_cycle.csv     (顾客,小类) 复购周期表（供复购召回）
    output/csvs/critic_weights_popularity.csv  商品热度 CRITIC 权重
    output/figures/12_促销敏感度分布.png
    output/figures/03_中类销售额Top15.png
    output/figures/04_小类销售额Top20.png
    output/figures/05_月度销售趋势.png
    output/figures/fe_价格带销售贡献.png
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import (load_clean, save_csv, set_style, savefig, topsis,
                    critic_weights, PALETTE, SEQ_CMAP, BINARY_COLORS)

EPS = 1e-9


# ---------------------------------------------------------------------------
# 商品级辅助：价格带（小类内分位）
# ---------------------------------------------------------------------------
def compute_price_rank(df):
    """每个商品在其小类内的价格分位 PriceRank ∈ [0,1]，及价格带标签。
    以「商品 × 小类」的平均单价为单位计算，避免同一商品多条记录重复加权。"""
    item_price = df.groupby(["cat_l3_code", "item_id"])["unit_price"].mean().reset_index()
    item_price["price_rank"] = item_price.groupby("cat_l3_code")["unit_price"].rank(pct=True)
    item_price["price_band"] = pd.cut(item_price["price_rank"], [0, 1/3, 2/3, 1.0],
                                      labels=["低价带", "中价带", "高价带"],
                                      include_lowest=True)
    return item_price[["item_id", "cat_l3_code", "price_rank", "price_band"]]


# ---------------------------------------------------------------------------
# 顾客画像
# ---------------------------------------------------------------------------
def build_customer_profile(df, price_rank):
    pos = df[df["is_return"] == 0].copy()
    D_max = df["sale_date"].max()
    pos = pos.merge(price_rank[["item_id", "price_rank"]], on="item_id", how="left")
    pos["price_rank"] = pos["price_rank"].fillna(0.5)

    g = pos.groupby("user_id")
    # RFM
    prof = pd.DataFrame(index=sorted(pos["user_id"].unique()))
    prof.index.name = "user_id"
    last_date = g["sale_date"].max()
    prof["R_最近购买间隔"] = (D_max - last_date).dt.days
    prof["F_购买频次"] = g["sale_date"].nunique()                 # 不同购买日数
    prof["M_消费金额"] = g["amount"].sum()
    prof["记录数"] = g.size()
    prof["客单价"] = prof["M_消费金额"] / prof["F_购买频次"].clip(lower=1)
    prof["平均件单价"] = g["amount"].sum() / g["quantity"].sum().clip(lower=EPS)

    # 类目偏好（大类金额占比）+ 类目熵（基于小类）
    l1_amt = pos.pivot_table(index="user_id", columns="cat_l1_name", values="amount",
                             aggfunc="sum", fill_value=0)
    l1_share = l1_amt.div(l1_amt.sum(axis=1) + EPS, axis=0)
    # 选主要大类占比作为画像列
    main_cats = ["蔬果", "休闲", "粮油", "日配", "洗化", "酒饮", "肉禽", "熟食"]
    for c in main_cats:
        prof[f"占比_{c}"] = l1_share[c] if c in l1_share else 0.0
    # 类目熵（小类层级，衡量偏好分散度）
    l3_amt = pos.pivot_table(index="user_id", columns="cat_l3_code", values="amount",
                             aggfunc="sum", fill_value=0)
    p = l3_amt.div(l3_amt.sum(axis=1) + EPS, axis=0).values
    with np.errstate(divide="ignore", invalid="ignore"):
        ent = -np.nansum(np.where(p > 0, p * np.log(p), 0.0), axis=1)
    prof["类目熵"] = pd.Series(ent, index=l3_amt.index)
    prof["小类购买数"] = (l3_amt > 0).sum(axis=1)

    # 生鲜消费占比
    fresh_amt = pos[pos["item_type"] == "生鲜"].groupby("user_id")["amount"].sum()
    prof["生鲜占比"] = (fresh_amt / prof["M_消费金额"]).fillna(0)

    # 促销敏感度
    promo_amt = pos[pos["is_promo"] == 1].groupby("user_id")["amount"].sum()
    promo_cnt = pos[pos["is_promo"] == 1].groupby("user_id").size()
    prof["促销金额占比"] = (promo_amt / prof["M_消费金额"]).fillna(0)
    prof["促销频次占比"] = (promo_cnt / prof["记录数"]).fillna(0)
    # α 用 CRITIC 自动确定（两指标合成）
    X_promo = prof[["促销金额占比", "促销频次占比"]].values
    w_promo, _ = critic_weights(X_promo)
    prof["促销敏感度"] = X_promo @ w_promo

    # 价格敏感度（低/高价带金额占比）
    low_amt = pos[pos["price_rank"] <= 1/3].groupby("user_id")["amount"].sum()
    high_amt = pos[pos["price_rank"] >= 2/3].groupby("user_id")["amount"].sum()
    prof["低价带占比"] = (low_amt / prof["M_消费金额"]).fillna(0)
    prof["高价带占比"] = (high_amt / prof["M_消费金额"]).fillna(0)
    # 顾客偏好价格分位（金额加权）
    pos["_amt_rank"] = pos["amount"] * pos["price_rank"]
    pref = pos.groupby("user_id")["_amt_rank"].sum() / pos.groupby("user_id")["amount"].sum()
    prof["偏好价格分位"] = pref.fillna(0.5)

    # 退货率
    ret = df[df["is_return"] == 1].groupby("user_id").size()
    all_cnt = df.groupby("user_id").size()
    prof["退货率"] = (ret / all_cnt).reindex(prof.index).fillna(0)

    prof = prof.reset_index()
    return prof, w_promo


# ---------------------------------------------------------------------------
# 复购周期表（顾客 × 小类）
# ---------------------------------------------------------------------------
def build_repurchase_cycle(df):
    pos = df[df["is_return"] == 0]
    D_now = df["sale_date"].max()
    rows = []
    # 仅对有 >=2 次购买的 (user,l3) 计算周期
    grp = pos.groupby(["user_id", "cat_l3_code"])["sale_date"]
    for (u, c), dates in grp:
        d = np.sort(dates.dt.normalize().unique())
        n = len(d)
        last = pd.Timestamp(d[-1])
        if n >= 2:
            gaps = np.diff(d).astype("timedelta64[D]").astype(float)
            cycle = gaps.mean()
        else:
            cycle = np.nan
        need = (D_now - last).days / (cycle + EPS) if cycle and not np.isnan(cycle) else np.nan
        rows.append((u, c, n, cycle, (D_now - last).days, need))
    cyc = pd.DataFrame(rows, columns=["user_id", "cat_l3_code", "购买次数",
                                      "平均复购周期天", "距今天数", "复购紧迫度"])
    return cyc


def aggregate_need(prof, cyc):
    # 顾客级复购紧迫度均值（仅多次购买的小类）
    need_mean = cyc.dropna(subset=["复购紧迫度"]).groupby("user_id")["复购紧迫度"].mean()
    cycle_mean = cyc.dropna(subset=["平均复购周期天"]).groupby("user_id")["平均复购周期天"].mean()
    prof = prof.merge(need_mean.rename("复购紧迫度均值"), on="user_id", how="left")
    prof = prof.merge(cycle_mean.rename("平均复购周期"), on="user_id", how="left")
    prof["复购紧迫度均值"] = prof["复购紧迫度均值"].fillna(0)
    prof["平均复购周期"] = prof["平均复购周期"].fillna(prof["平均复购周期"].median())
    return prof


# ---------------------------------------------------------------------------
# 商品画像
# ---------------------------------------------------------------------------
def build_product_profile(df, price_rank):
    pos = df[df["is_return"] == 0]
    g = pos.groupby("item_id")
    prof = pd.DataFrame(index=sorted(pos["item_id"].unique()))
    prof.index.name = "item_id"
    # 类目信息（取众数/首条）
    meta = pos.groupby("item_id").agg(
        cat_l1_name=("cat_l1_name", "first"), cat_l2_name=("cat_l2_name", "first"),
        cat_l3_name=("cat_l3_name", "first"), cat_l3_code=("cat_l3_code", "first"),
        item_type=("item_type", "first"), unit=("unit", "first"),
        spec=("spec", "first"))
    prof = prof.join(meta)
    prof["销售金额"] = g["amount"].sum()
    prof["销售数量"] = g["quantity"].sum()
    prof["销售笔数"] = g.size()
    prof["平均单价"] = g["unit_price"].mean()
    prof["购买人数"] = g["user_id"].nunique()
    # 复购率：购买>=2次的人数 / 购买人数
    buyer_freq = pos.groupby(["item_id", "user_id"]).size()
    repeat_buyers = (buyer_freq >= 2).groupby(level=0).sum().reindex(prof.index).fillna(0)
    prof["复购率"] = (repeat_buyers / prof["购买人数"]).fillna(0)
    # 复购率经验贝叶斯收缩（避免购买人数极小时虚高为1.0）：朝全局均值收缩，K为先验强度
    global_rep = repeat_buyers.sum() / prof["购买人数"].sum()
    K = 10.0
    prof["复购率_平滑"] = (repeat_buyers + global_rep * K) / (prof["购买人数"] + K)
    # 促销属性：该商品促销笔数占比
    promo_rate = pos.groupby("item_id")["is_promo"].mean()
    prof["促销占比"] = promo_rate
    # 价格带
    prof = prof.merge(price_rank[["item_id", "price_rank", "price_band"]],
                      on="item_id", how="left")

    # 综合热度 = TOPSIS(销售金额, 销售数量, 购买人数, 复购率_平滑) 权重由 CRITIC 自动
    # 金额/数量/人数做 log1p 压缩长尾，避免极端值主导
    Xraw = prof[["销售金额", "销售数量", "购买人数"]].values
    Xlog = np.log1p(np.clip(Xraw, 0, None))
    X = np.column_stack([Xlog, prof["复购率_平滑"].values])
    w, info = critic_weights(X)
    pop, _ = topsis(X, w)
    prof["综合热度"] = pop
    prof["热度排名"] = prof["综合热度"].rank(ascending=False).astype(int)
    return prof, w


def main():
    set_style()
    df = load_clean()
    price_rank = compute_price_rank(df)

    # 顾客画像
    cust, w_promo = build_customer_profile(df, price_rank)
    cyc = build_repurchase_cycle(df)
    cust = aggregate_need(cust, cyc)
    save_csv(cust.round(4), "customer_profile.csv")
    save_csv(cyc.round(3), "repurchase_cycle.csv")
    print(f"顾客画像: {cust.shape}, 复购周期表: {cyc.shape}")
    print("促销敏感度 CRITIC 权重 [金额占比, 频次占比]:", np.round(w_promo, 4))

    # 商品画像
    prod, w_pop = build_product_profile(df, price_rank)
    save_csv(prod.round(4), "product_profile.csv")
    wdf = pd.DataFrame({"指标": ["销售金额(log)", "销售数量(log)", "购买人数(log)", "复购率_平滑"],
                        "CRITIC权重": np.round(w_pop, 4)})
    save_csv(wdf, "critic_weights_popularity.csv")
    print(f"商品画像: {prod.shape}")
    print("商品热度 CRITIC 权重:", dict(zip(wdf["指标"], wdf["CRITIC权重"])))

    _plots(df, cust, prod)
    return cust, prod, cyc


def _plots(df, cust, prod):
    pos = df[df["is_return"] == 0]
    # 图12：促销敏感度分布（直方+核密度近似）
    fig, ax = plt.subplots(figsize=(8, 4.5))
    vals = cust["促销敏感度"].values
    ax.hist(vals, bins=40, color=PALETTE[0], alpha=0.75, edgecolor="white")
    ax.set_xlabel("促销敏感度")
    ax.set_ylabel("顾客数")
    savefig(fig, "12_促销敏感度分布.png")

    # 图3：中类销售额 Top15（条形）
    l2 = pos.groupby("cat_l2_name")["amount"].sum().sort_values(ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(l2.index[::-1], l2.values[::-1], color=PALETTE[3], edgecolor="white")
    ax.set_xlabel("销售金额 (元)")
    savefig(fig, "03_中类销售额Top15.png")

    # 图4：小类销售额 Top20（条形）
    l3 = pos.groupby("cat_l3_name")["amount"].sum().sort_values(ascending=False).head(20)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(l3.index[::-1], l3.values[::-1], color=PALETTE[2], edgecolor="white")
    ax.set_xlabel("销售金额 (元)")
    savefig(fig, "04_小类销售额Top20.png")

    # 图5：月度销售趋势（按周聚合折线，更细腻）
    daily = pos.groupby("sale_date")["amount"].sum()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(daily.index, daily.values, color=PALETTE[1], lw=1.4, marker="o",
            markersize=3, markerfacecolor="white")
    ax.set_xlabel("日期")
    ax.set_ylabel("日销售金额 (元)")
    fig.autofmt_xdate()
    savefig(fig, "05_月度销售趋势.png")

    # 价格带销售贡献（堆叠柱：各大类下低/中/高价带占比）
    pr = prod.dropna(subset=["price_band"])
    merged = pos.merge(pr[["item_id", "price_band"]], on="item_id", how="inner")
    pivot = merged.pivot_table(index="cat_l1_name", columns="price_band",
                               values="amount", aggfunc="sum", fill_value=0,
                               observed=True)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index].head(10)
    share = pivot.div(pivot.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(len(share))
    bands = [b for b in ["低价带", "中价带", "高价带"] if b in share.columns]
    for i, b in enumerate(bands):
        ax.bar(share.index, share[b].values, bottom=bottom,
               color=PALETTE[i], label=b, edgecolor="white", width=0.7)
        bottom += share[b].values
    ax.set_ylabel("价格带销售额占比")
    ax.legend(ncol=3)
    fig.autofmt_xdate(rotation=30)
    savefig(fig, "fe_价格带销售贡献.png")


if __name__ == "__main__":
    main()
