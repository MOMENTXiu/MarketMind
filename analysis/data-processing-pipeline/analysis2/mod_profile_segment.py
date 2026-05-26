# -*- coding: utf-8 -*-
"""普适分析模块 2：顾客画像(RFM+扩展) + 聚类分群。按可用字段自适应。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score
from config_3 import savefig, save_csv, save_pkl, positive, PALETTE


def build_profile(df):
    pos = positive(df)
    has = lambda c: c in pos.columns
    Dmax = pos["sale_date"].max()
    g = pos.groupby("user_id")
    prof = pd.DataFrame(index=sorted(pos["user_id"].unique())); prof.index.name = "user_id"
    prof["R_最近间隔"] = (Dmax - g["sale_date"].max()).dt.days
    prof["F_频次"] = g["order_id"].nunique() if has("order_id") else g["sale_date"].nunique()
    prof["M_金额"] = g["amount"].sum() if has("amount") else g.size()
    prof["记录数"] = g.size()
    prof["客单价"] = prof["M_金额"] / prof["F_频次"].clip(lower=1)
    if has("quantity"):
        prof["总数量"] = g["quantity"].sum()
    # 类目熵（偏好分散度）
    if has("cat_l1_name") and has("amount"):
        piv = pos.pivot_table(index="user_id", columns="cat_l1_name", values="amount",
                              aggfunc="sum", fill_value=0)
        p = piv.div(piv.sum(axis=1) + 1e-9, axis=0).values
        prof["类目熵"] = -np.nansum(np.where(p > 0, p * np.log(p), 0), axis=1)
    if has("is_promo") and has("amount"):
        pa = pos[pos["is_promo"] == 1].groupby("user_id")["amount"].sum()
        prof["促销金额占比"] = (pa / prof["M_金额"]).reindex(prof.index).fillna(0)
    if has("discount"):
        prof["平均折扣"] = g["discount"].mean()
    if has("profit"):
        prof["利润率"] = (g["profit"].sum() / prof["M_金额"].replace(0, np.nan)).fillna(0)
    if has("age"):
        prof["年龄"] = g["age"].first().astype(float)
    return prof.reset_index()


def run(df, dataset, cap):
    prof = build_profile(df)
    feats = [c for c in prof.columns if c not in ("user_id",)]
    # log 压缩高偏特征
    Xdf = prof[feats].copy()
    for c in ["F_频次", "M_金额", "记录数", "客单价", "总数量"]:
        if c in Xdf:
            Xdf[c] = np.log1p(Xdf[c].clip(lower=0))
    Xs = StandardScaler().fit_transform(Xdf.fillna(Xdf.median()).values)

    # 选 k：扫描 2-7 报告；在营销可落地区间 [3,6] 内择最优轮廓（数据过小才退化到 2）。
    # 零售画像多为连续谱，纯轮廓常偏好 k=2，但 3-6 群更具营销可寻址性（参见项目1两层分群思路）。
    import numpy as _np
    idx = _np.random.default_rng(42).choice(len(Xs), min(5000, len(Xs)), replace=False)
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
    save_csv(pd.DataFrame(scan), dataset, "segment_kscan.csv")

    # 群体画像
    aggd = {"人数": ("user_id", "size")}
    for c in feats:
        aggd[c] = (c, "mean")
    sp = prof.groupby("分群").agg(**aggd).round(3)
    sp["人数占比"] = (sp["人数"] / len(prof)).round(3)
    if "M_金额" in sp:
        sp["销售贡献占比"] = ((sp["人数"] * sp["M_金额"]) / (sp["人数"] * sp["M_金额"]).sum()).round(3)
    save_csv(sp.reset_index(), dataset, "segment_profile.csv")
    save_csv(prof[["user_id", "分群"]], dataset, "customer_segments.csv")
    save_pkl({"kmeans": km, "feats": feats}, dataset, "segment_model.pkl")

    _plots(prof, sp, feats, dataset, K, sil)
    return {"n_segments": int(K), "silhouette": round(sil, 4),
            "top_contrib_seg": int(sp["销售贡献占比"].idxmax()) if "销售贡献占比" in sp else None,
            "features_used": feats}


def _plots(prof, sp, feats, dataset, K, sil):
    # 散点（R vs M 或 前两特征）
    fig, ax = plt.subplots(figsize=(8, 6))
    xx = "M_金额" if "M_金额" in prof else feats[0]
    yy = "F_频次" if "F_频次" in prof else feats[1]
    for c in sorted(prof["分群"].unique()):
        m = prof["分群"] == c
        ax.scatter(np.log1p(prof[m][xx]), np.log1p(prof[m][yy]), s=10, alpha=0.5,
                   color=PALETTE[c % len(PALETTE)], label=f"群{c}", linewidths=0)
    ax.set_xlabel(f"log({xx})"); ax.set_ylabel(f"log({yy})"); ax.legend()
    savefig(fig, dataset, "segment_聚类散点.png")

    # 雷达
    rf = [c for c in ["R_最近间隔", "F_频次", "M_金额", "客单价", "类目熵",
                      "促销金额占比", "平均折扣", "利润率", "年龄"] if c in sp.columns][:7]
    if len(rf) >= 3:
        cen = sp[rf]; cn = (cen - cen.min()) / (cen.max() - cen.min() + 1e-9)
        ang = np.linspace(0, 2 * np.pi, len(rf), endpoint=False).tolist(); ang += ang[:1]
        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
        for i, (c, row) in enumerate(cn.iterrows()):
            v = row.tolist() + row.tolist()[:1]
            ax.plot(ang, v, color=PALETTE[i % len(PALETTE)], lw=2, label=f"群{c}")
            ax.fill(ang, v, color=PALETTE[i % len(PALETTE)], alpha=0.1)
        ax.set_xticks(ang[:-1]); ax.set_xticklabels(rf, fontsize=9); ax.set_yticklabels([])
        ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.1), fontsize=8)
        savefig(fig, dataset, "segment_雷达画像.png")

    # 群体销售贡献
    if "销售贡献占比" in sp:
        s = sp.sort_values("销售贡献占比", ascending=False)
        x = np.arange(len(s))
        fig, ax = plt.subplots(figsize=(8, 4.6))
        ax.bar(x - 0.2, s["人数占比"], 0.4, color=PALETTE[0], label="人数占比", edgecolor="white")
        ax.bar(x + 0.2, s["销售贡献占比"], 0.4, color=PALETTE[1], label="销售贡献占比", edgecolor="white")
        ax.set_xticks(x); ax.set_xticklabels([f"群{i}" for i in s.index]); ax.set_ylabel("占比"); ax.legend()
        savefig(fig, dataset, "segment_销售贡献.png")
