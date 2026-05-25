# -*- coding: utf-8 -*-
"""
阶段 3：顾客分群实验（思路文档 §7、§14.1）
E1 GMM(baseline) | E2 UMAP+HDBSCAN(主模型) | E3 AutoEncoder+GMM | E4 UMAP+HDBSCAN+GMM(融合)
评价：Silhouette / Davies-Bouldin / Calinski-Harabasz + 群体规模 + 销售贡献差异 + 营销解释性。

产出：
  output/csvs/customer_segments_hdbscan.csv   主分群(硬标签+语义)
  output/csvs/customer_segments_gmm.csv       GMM 软分群概率
  output/csvs/segment_profile.csv             群体画像均值
  output/csvs/clustering_model_comparison.csv 四模型指标对比
  output/figures/08_UMAP嵌入分布.png
  output/figures/09_HDBSCAN群体分布.png
  output/figures/10_群体雷达画像.png
  output/figures/11_群体销售贡献.png
  output/figures/cl_GMM_BIC曲线.png
  output/figures/cl_模型指标对比.png
  output/pkls/clustering_models.pkl
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
import umap
import hdbscan
import torch
import torch.nn as nn

from config import (load_clean, save_csv, set_style, savefig, save_pkl,
                    PALETTE, CSV_DIR)

RNG = 42
np.random.seed(RNG)
torch.manual_seed(RNG)

# 用于分群的画像特征（思路 §7.2）
FEATURES = ["R_最近购买间隔", "F_购买频次", "M_消费金额", "客单价", "类目熵",
            "占比_蔬果", "占比_粮油", "占比_日配", "占比_休闲", "小类购买数",
            "促销金额占比", "促销频次占比", "低价带占比", "高价带占比",
            "生鲜占比", "复购紧迫度均值"]
LOG_FEATS = ["F_购买频次", "M_消费金额", "客单价", "小类购买数", "复购紧迫度均值"]


def load_features():
    cust = pd.read_csv(f"{CSV_DIR}/customer_profile.csv", encoding="utf-8-sig",
                       dtype={"user_id": str})
    Xdf = cust[FEATURES].copy()
    for c in LOG_FEATS:
        Xdf[c] = np.log1p(Xdf[c].clip(lower=0))
    scaler = StandardScaler()
    Xs = scaler.fit_transform(Xdf.values)
    return cust, Xs, scaler


# ---------------------------------------------------------------------------
# E3: AutoEncoder (torch)
# ---------------------------------------------------------------------------
class AE(nn.Module):
    def __init__(self, d_in, d_bottle=5):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d_in, 32), nn.ReLU(),
                                 nn.Linear(32, 16), nn.ReLU(),
                                 nn.Linear(16, d_bottle))
        self.dec = nn.Sequential(nn.Linear(d_bottle, 16), nn.ReLU(),
                                 nn.Linear(16, 32), nn.ReLU(),
                                 nn.Linear(32, d_in))

    def forward(self, x):
        z = self.enc(x)
        return self.dec(z), z


def train_ae(Xs, d_bottle=5, epochs=300):
    X = torch.tensor(Xs, dtype=torch.float32)
    model = AE(Xs.shape[1], d_bottle)
    opt = torch.optim.Adam(model.parameters(), lr=1e-2, weight_decay=1e-5)
    lossf = nn.MSELoss()
    for ep in range(epochs):
        opt.zero_grad()
        rec, _ = model(X)
        loss = lossf(rec, X)
        loss.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        _, z = model(X)
    return z.numpy(), float(loss.item())


# ---------------------------------------------------------------------------
# 指标
# ---------------------------------------------------------------------------
def cluster_metrics(eval_space, labels):
    """在【原始标准化特征空间】统一评估各模型标签（公平对比），排除噪声(-1)。"""
    mask = labels != -1
    uniq = set(labels[mask].tolist())
    if len(uniq) < 2 or mask.sum() < 10:
        return dict(silhouette=np.nan, dbi=np.nan, ch=np.nan,
                    n_clusters=len(uniq), noise_rate=float((labels == -1).mean()))
    return dict(
        silhouette=silhouette_score(eval_space[mask], labels[mask]),
        dbi=davies_bouldin_score(eval_space[mask], labels[mask]),
        ch=calinski_harabasz_score(eval_space[mask], labels[mask]),
        n_clusters=len(uniq),
        noise_rate=float((labels == -1).mean()))


# ---------------------------------------------------------------------------
# 语义标签：依据群体画像质心映射到 7 类营销原型（思路 §7.4）
# ---------------------------------------------------------------------------
def name_segments(cust, labels, label_col="cluster"):
    df = cust.copy()
    df[label_col] = labels
    valid = df[df[label_col] != -1]
    prof = valid.groupby(label_col).agg(
        人数=("user_id", "size"),
        R=("R_最近购买间隔", "mean"), F=("F_购买频次", "mean"),
        M=("M_消费金额", "mean"), 促销=("促销敏感度", "mean"),
        生鲜=("生鲜占比", "mean"), 类目熵=("类目熵", "mean"),
        低价带=("低价带占比", "mean"))
    # 全局参考分位
    med = valid[["R_最近购买间隔", "F_购买频次", "M_消费金额", "促销敏感度",
                 "生鲜占比", "类目熵", "低价带占比"]].median()
    names = {}
    for cid, r in prof.iterrows():
        if r["M"] >= med["M_消费金额"] and r["F"] >= med["F_购买频次"] and r["R"] <= med["R_最近购买间隔"]:
            name = "高价值稳定型"
        elif r["R"] >= valid["R_最近购买间隔"].quantile(0.7) and r["M"] >= med["M_消费金额"]:
            name = "流失预警型"
        elif r["生鲜"] >= valid["生鲜占比"].quantile(0.65):
            name = "生鲜高频型"
        elif r["促销"] >= valid["促销敏感度"].quantile(0.65) or r["低价带"] >= valid["低价带占比"].quantile(0.7):
            name = "促销敏感型"
        elif r["类目熵"] >= valid["类目熵"].quantile(0.65):
            name = "跨类探索型"
        elif r["类目熵"] <= valid["类目熵"].quantile(0.35):
            name = "类目集中型"
        else:
            name = "低频偶发型"
        names[cid] = name
    # 同名去重：附加编号
    seen = {}
    final = {}
    for cid, nm in sorted(names.items()):
        seen[nm] = seen.get(nm, 0) + 1
        final[cid] = nm if seen[nm] == 1 else f"{nm}{seen[nm]}"
    final[-1] = "噪声/边界用户"
    return prof, final


def main():
    set_style()
    cust, Xs, scaler = load_features()
    print(f"分群样本: {Xs.shape}")
    results = {}
    models = {}

    # ---------- E1: GMM baseline ----------
    bics = []
    for k in range(2, 9):
        gm = GaussianMixture(n_components=k, covariance_type="full",
                             random_state=RNG, n_init=3, reg_covar=1e-4).fit(Xs)
        bics.append((k, gm.bic(Xs)))
    best_k = min(bics, key=lambda t: t[1])[0]
    gmm = GaussianMixture(n_components=best_k, covariance_type="full",
                          random_state=RNG, n_init=5, reg_covar=1e-4).fit(Xs)
    gmm_labels = gmm.predict(Xs)
    gmm_proba = gmm.predict_proba(Xs)
    results["E1_GMM"] = cluster_metrics(Xs, gmm_labels)
    models["gmm"] = gmm
    print(f"E1 GMM: best_k={best_k} (BIC), {results['E1_GMM']}")

    # ---------- E2: UMAP + HDBSCAN ----------
    # UMAP 2D 嵌入（聚类与可视化同一空间，保证图与簇一致），对 min_cluster_size 网格搜索
    reducer2d = umap.UMAP(n_neighbors=30, min_dist=0.05, n_components=2,
                          metric="euclidean", random_state=RNG)
    emb2d = reducer2d.fit_transform(Xs)
    emb_hi = emb2d  # 软归属/E4 复用同一嵌入
    best = None
    for mcs in [25, 30, 35, 40, 50, 60]:
        cl = hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=8,
                             cluster_selection_method="eom")
        lab = cl.fit_predict(emb2d)
        m = cluster_metrics(emb2d, lab)   # 嵌入空间轮廓用于模型选择
        nc, nr, sil = m["n_clusters"], m["noise_rate"], m["silhouette"]
        ok = (nc >= 2) and (nr < 0.15)   # 干净的自然宏观结构：低噪声、至少2群
        score = sil if ok else sil - 10.0  # 不满足约束的强降权（拒绝高噪声过碎结果）
        print(f"  [扫描] min_cluster_size={mcs}: 群体={nc}, 噪声={nr:.3f}, 嵌入轮廓={sil:.3f}, 合格={ok}")
        if best is None or score > best[0]:
            best = (score, mcs, cl, lab)
    _, best_mcs, clusterer, hdb_labels = best
    results["E2_UMAP_HDBSCAN"] = cluster_metrics(Xs, hdb_labels)
    results["E2_UMAP_HDBSCAN"]["silhouette_嵌入空间"] = cluster_metrics(emb2d, hdb_labels)["silhouette"]
    models["umap2d"] = reducer2d
    models["hdbscan"] = clusterer
    print(f"E2 UMAP+HDBSCAN: 选定 min_cluster_size={best_mcs}, {results['E2_UMAP_HDBSCAN']}")

    # ---------- E3: AutoEncoder + GMM （最终落地的 7 群软分群主模型） ----------
    z, ae_loss = train_ae(Xs, d_bottle=5)
    gmm_ae = GaussianMixture(n_components=best_k, covariance_type="full",
                             random_state=RNG, n_init=5, reg_covar=1e-4).fit(z)
    ae_labels = gmm_ae.predict(z)
    ae_proba = gmm_ae.predict_proba(z)
    results["E3_AE_GMM"] = cluster_metrics(Xs, ae_labels)   # 同样在原始空间评估
    models["ae_gmm"] = gmm_ae
    print(f"E3 AE+GMM: AE重构MSE={ae_loss:.4f}, {results['E3_AE_GMM']}")

    # ---------- E4: UMAP+HDBSCAN (自然群体) + GMM(软归属) ----------
    # 融合：HDBSCAN 硬标签为主；在高维 UMAP 空间用 GMM(组件数=HDBSCAN簇数) 输出软归属概率，
    #       并据此为噪声点指派最近群体（消解噪声，提升覆盖）。
    n_nat = max(results["E2_UMAP_HDBSCAN"]["n_clusters"], 2)
    gmm_soft = GaussianMixture(n_components=n_nat, covariance_type="full",
                               random_state=RNG, n_init=5, reg_covar=1e-4).fit(emb_hi)
    soft_proba = gmm_soft.predict_proba(emb_hi)
    # E4 标签：非噪声沿用 HDBSCAN；噪声点用软 GMM 最大概率归属
    e4_labels = hdb_labels.copy()
    noise_mask = hdb_labels == -1
    e4_labels[noise_mask] = gmm_soft.predict(emb_hi)[noise_mask] + 1000  # 临时偏移避免与hdb簇号冲突
    # 将噪声点映射到与其软GMM组件重合度最高的HDBSCAN簇
    soft_hard = gmm_soft.predict(emb_hi)
    comp2hdb = {}
    for comp in range(n_nat):
        sel = (soft_hard == comp) & (~noise_mask)
        if sel.sum() > 0:
            comp2hdb[comp] = pd.Series(hdb_labels[sel]).mode().iloc[0]
    e4_labels = hdb_labels.copy()
    for i in np.where(noise_mask)[0]:
        e4_labels[i] = comp2hdb.get(soft_hard[i], hdb_labels[~noise_mask][0])
    results["E4_UMAP_HDBSCAN_GMM"] = cluster_metrics(Xs, e4_labels)
    models["gmm_soft"] = gmm_soft

    # ====================================================================
    # 最终落地分群方案（依据指标对比 + 数据连续谱特性，灵活择优）：
    #   · 营销可落地的 7 群软分群  = AE+GMM（k=7，原始空间指标全面优于裸 GMM，0 噪声，含软概率）
    #   · 自然宏观结构验证        = UMAP+HDBSCAN（数据呈双模态连续谱，2 个稳健大群）
    #   · 边界/噪声用户           = HDBSCAN 噪声点（营销可单独低成本触达）
    # ====================================================================
    prof, seg_names = name_segments(cust, ae_labels)        # 对 7 个 AE+GMM 群语义命名
    macro_name = {c: f"宏观群{c}" for c in set(hdb_labels.tolist())}
    macro_name[-1] = "边界用户"

    cust_out = cust[["user_id"]].copy()
    cust_out["segment_id"] = ae_labels
    cust_out["segment"] = cust_out["segment_id"].map(seg_names)
    cust_out["归属置信度"] = ae_proba.max(axis=1).round(4)
    cust_out["宏观结构"] = pd.Series(hdb_labels).map(macro_name).values
    cust_out["是否边界用户"] = (hdb_labels == -1).astype(int)
    cust_out["x_umap"] = emb2d[:, 0].round(4)
    cust_out["y_umap"] = emb2d[:, 1].round(4)
    save_csv(cust_out, "customer_segments_hdbscan.csv")   # 主分群结果（沿用思路文档命名）

    # GMM 软分群表（AE+GMM 的软归属概率，列名带语义）
    gmm_df = cust[["user_id"]].copy()
    for k in range(best_k):
        gmm_df[f"P_{seg_names.get(k, k)}"] = ae_proba[:, k].round(4)
    gmm_df["硬标签"] = ae_labels
    gmm_df["语义群体"] = pd.Series(ae_labels).map(seg_names).values
    save_csv(gmm_df, "customer_segments_gmm.csv")

    # 群体画像表（7 个营销群体 + 销售贡献）
    prof = prof.reset_index()
    prof["语义群体"] = prof["cluster"].map(seg_names)
    total_M = cust["M_消费金额"].sum()
    prof["群体销售额"] = prof["人数"] * prof["M"]
    prof["销售贡献占比"] = (prof["群体销售额"] / total_M).round(4)
    prof["人数占比"] = (prof["人数"] / len(cust)).round(4)
    save_csv(prof.round(3), "segment_profile.csv")

    # 模型对比表（统一在原始特征空间评估）
    comp = pd.DataFrame(results).T.reset_index().rename(columns={"index": "实验"})
    comp = comp.rename(columns={"silhouette": "轮廓系数", "dbi": "DB指数",
                                "ch": "CH指数", "n_clusters": "群体数",
                                "noise_rate": "噪声占比",
                                "silhouette_嵌入空间": "轮廓系数_嵌入空间"})
    order = ["实验", "轮廓系数", "DB指数", "CH指数", "群体数", "噪声占比", "轮廓系数_嵌入空间"]
    comp = comp[[c for c in order if c in comp.columns]]
    save_csv(comp.round(4), "clustering_model_comparison.csv")
    print("\n模型对比:\n", comp.round(4).to_string(index=False))

    save_pkl({"scaler": scaler, "features": FEATURES, "log_feats": LOG_FEATS,
              "models": models, "best_k": best_k, "seg_names": seg_names}, "clustering_models.pkl")

    _plots(cust, Xs, emb2d, ae_labels, hdb_labels, bics, comp, prof, seg_names, macro_name)
    return cust_out, prof, comp


def _plots(cust, Xs, emb2d, ae_labels, hdb_labels, bics, comp, prof, seg_names, macro_name):
    # 图8：UMAP 嵌入（按 7 个营销群体 AE+GMM 上色）
    fig, ax = plt.subplots(figsize=(8, 6))
    for i, c in enumerate(sorted(set(ae_labels.tolist()))):
        m = ae_labels == c
        ax.scatter(emb2d[m, 0], emb2d[m, 1], color=PALETTE[i % len(PALETTE)],
                   s=11, alpha=0.75, linewidths=0, label=seg_names.get(c, str(c)))
    ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
    ax.legend(loc="best", fontsize=8, ncol=2)
    savefig(fig, "08_UMAP嵌入分布.png")

    # 图9：HDBSCAN 自然宏观结构（双模态 + 边界用户）
    fig, ax = plt.subplots(figsize=(7.5, 6))
    for i, c in enumerate(sorted(set(hdb_labels.tolist()))):
        m = hdb_labels == c
        if c == -1:
            ax.scatter(emb2d[m, 0], emb2d[m, 1], c="#BBBBBB", s=8, alpha=0.5,
                       label="边界用户", linewidths=0)
        else:
            ax.scatter(emb2d[m, 0], emb2d[m, 1], color=PALETTE[i % len(PALETTE)],
                       s=12, alpha=0.8, label=macro_name.get(c, f"宏观群{c}"), linewidths=0)
    ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
    ax.legend(loc="best", fontsize=9)
    savefig(fig, "09_HDBSCAN群体分布.png")

    # 图10：群体雷达画像（7 营销群体，关键特征均值 min-max 归一）
    radar_feats = ["M_消费金额", "F_购买频次", "促销敏感度", "生鲜占比",
                   "类目熵", "低价带占比", "高价带占比"]
    valid = cust.copy()
    valid["cluster"] = ae_labels
    cen = valid.groupby("cluster")[radar_feats].mean()
    cen_n = (cen - cen.min()) / (cen.max() - cen.min() + 1e-9)
    angles = np.linspace(0, 2 * np.pi, len(radar_feats), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    for i, (cid, row) in enumerate(cen_n.iterrows()):
        vals = row.tolist() + row.tolist()[:1]
        ax.plot(angles, vals, color=PALETTE[i % len(PALETTE)], lw=2,
                label=seg_names.get(cid, str(cid)))
        ax.fill(angles, vals, color=PALETTE[i % len(PALETTE)], alpha=0.12)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(radar_feats, fontsize=10)
    ax.set_yticklabels([])
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8)
    savefig(fig, "10_群体雷达画像.png")

    # 图11：群体销售贡献（人数占比 vs 销售贡献占比，双柱）
    pr = prof[prof["cluster"] != -1].sort_values("销售贡献占比", ascending=False)
    x = np.arange(len(pr))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - 0.2, pr["人数占比"], width=0.4, color=PALETTE[0], label="人数占比",
           edgecolor="white")
    ax.bar(x + 0.2, pr["销售贡献占比"], width=0.4, color=PALETTE[1],
           label="销售贡献占比", edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(pr["语义群体"], rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("占比")
    ax.legend()
    savefig(fig, "11_群体销售贡献.png")

    # GMM BIC 曲线
    ks = [b[0] for b in bics]; vs = [b[1] for b in bics]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(ks, vs, marker="o", color=PALETTE[4], lw=1.8, markerfacecolor="white")
    bk = ks[int(np.argmin(vs))]
    ax.axvline(bk, color=PALETTE[1], ls="--", lw=1.2)
    ax.set_xlabel("GMM 组件数 k"); ax.set_ylabel("BIC")
    savefig(fig, "cl_GMM_BIC曲线.png")

    # 模型指标对比（轮廓系数 越大越好 / DBI 越小越好）
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    c = comp.set_index("实验")
    axes[0].bar(c.index, c["轮廓系数"], color=PALETTE[2], edgecolor="white")
    axes[0].set_ylabel("轮廓系数 (越大越好)")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(c.index, c["DB指数"], color=PALETTE[3], edgecolor="white")
    axes[1].set_ylabel("DB指数 (越小越好)")
    axes[1].tick_params(axis="x", rotation=20)
    for ax in axes:
        for lab in ax.get_xticklabels():
            lab.set_ha("right"); lab.set_fontsize(8)
    savefig(fig, "cl_模型指标对比.png")


if __name__ == "__main__":
    main()
