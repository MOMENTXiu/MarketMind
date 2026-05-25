# -*- coding: utf-8 -*-
"""
深化模块 G/C：价格弹性（DML）+ 鲁棒性检验
G. 需求价格弹性：log(销量)对 log(单价) 的去偏因果弹性（DML 连续处理），整体 + 分大类。
C. 鲁棒性检验：
   C1 关联规则统计显著性（卡方独立性检验 + Bonferroni 校正）
   C2 聚类稳定性（bootstrap 重抽样 GMM，ARI 一致性）

产出：
  output/csvs/price_elasticity.csv        整体+分大类弹性
  output/csvs/rule_significance.csv         规则显著性检验
  output/csvs/cluster_stability.csv         聚类稳定性
  output/figures/el_价格弹性.png
  output/figures/el_规则显著性.png
  output/figures/el_聚类稳定性.png
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules

from config import load_clean, save_csv, set_style, savefig, PALETTE, CSV_DIR
from causal_dml import dml_partial_linear

RNG = 42


# ===========================================================================
# G. 价格弹性（DML 连续处理）
# ===========================================================================
def price_elasticity(df):
    pos = df[df["is_return"] == 0].copy()
    pos = pos[(pos["unit_price"] > 0) & (pos["quantity"] > 0)]
    # 商品购买人数（热度代理）
    buyers = pos.groupby("item_id")["user_id"].nunique()
    pos["log_buyers"] = np.log1p(pos["item_id"].map(buyers))
    pos["logP"] = np.log(pos["unit_price"])
    pos["logQ"] = np.log(pos["quantity"])

    def run(sub, ctrl_col):
        ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore", min_frequency=20)
        cat = ohe.fit_transform(sub[[ctrl_col]])
        num = sub[["is_promo", "weekday", "is_weekend", "sale_month", "log_buyers"]].values
        X = np.hstack([num, cat])
        T = sub["logP"].values
        Y = sub["logQ"].values
        res = dml_partial_linear(X, T, Y, n_folds=5, discrete_treatment=False)
        return res

    rows = []
    # 整体（用中类做类目控制）
    r = run(pos, "cat_l2_name")
    rows.append({"范围": "整体", "价格弹性": round(r["theta"], 3),
                 "标准误": round(r["se"], 3), "95%CI下": round(r["ci95"][0], 3),
                 "95%CI上": round(r["ci95"][1], 3), "样本数": r["n"]})
    # 分大类（用小类做类目控制）
    for l1, sub in pos.groupby("cat_l1_name"):
        if len(sub) < 300 or sub["cat_l3_name"].nunique() < 2:
            continue
        try:
            r = run(sub, "cat_l3_name")
            rows.append({"范围": l1, "价格弹性": round(r["theta"], 3),
                         "标准误": round(r["se"], 3), "95%CI下": round(r["ci95"][0], 3),
                         "95%CI上": round(r["ci95"][1], 3), "样本数": r["n"]})
        except Exception as e:
            print("skip", l1, str(e)[:40])
    el = pd.DataFrame(rows)
    el["弹性类型"] = np.where(el["价格弹性"] < -1, "富有弹性(可促销走量)",
                          np.where(el["价格弹性"] < 0, "缺乏弹性(可提价提毛利)", "异常(正)"))
    return el


# ===========================================================================
# C1. 关联规则显著性（卡方）
# ===========================================================================
def rule_significance(df, min_support=0.01):
    pos = df[df["is_return"] == 0]
    g = pos.groupby(["user_id", "sale_date"])["cat_l3_name"].apply(lambda s: sorted(set(s)))
    tx = [t for t in g.tolist() if len(t) >= 2]
    N = len(tx)
    te = TransactionEncoder(); arr = te.fit_transform(tx)
    dfb = pd.DataFrame(arr, columns=te.columns_)
    fq = fpgrowth(dfb, min_support=min_support, use_colnames=True, max_len=2)
    rules = association_rules(fq, metric="confidence", min_threshold=0.2)
    rules = rules[(rules["lift"] >= 1.1) & (rules["consequents"].apply(len) == 1) &
                  (rules["antecedents"].apply(len) == 1)]
    presence = {c: dfb[c].values for c in dfb.columns}
    rows = []
    for _, r in rules.iterrows():
        a = list(r["antecedents"])[0]; b = list(r["consequents"])[0]
        A = presence[a]; B = presence[b]
        n11 = int((A & B).sum()); n10 = int((A & ~B).sum())
        n01 = int((~A & B).sum()); n00 = int((~A & ~B).sum())
        table = np.array([[n11, n10], [n01, n00]])
        chi2, p, _, _ = chi2_contingency(table, correction=True)
        rows.append({"前项": a, "后项": b, "支持度": round(r["support"], 4),
                     "提升度": round(r["lift"], 3), "卡方": round(chi2, 2),
                     "p值": p})
    sig = pd.DataFrame(rows).sort_values("卡方", ascending=False)
    m = len(sig)
    sig["Bonferroni阈值"] = 0.05 / max(m, 1)
    sig["是否显著"] = np.where(sig["p值"] < 0.05 / max(m, 1), "显著", "不显著")
    sig["p值"] = sig["p值"].apply(lambda x: f"{x:.2e}")
    return sig


# ===========================================================================
# C2. 聚类稳定性（bootstrap ARI）
# ===========================================================================
def cluster_stability(n_boot=25, k=7):
    cust = pd.read_csv(f"{CSV_DIR}/customer_profile.csv", encoding="utf-8-sig")
    feats = ["R_最近购买间隔", "F_购买频次", "M_消费金额", "客单价", "类目熵",
             "占比_蔬果", "占比_粮油", "占比_日配", "占比_休闲", "小类购买数",
             "促销金额占比", "促销频次占比", "低价带占比", "高价带占比",
             "生鲜占比", "复购紧迫度均值"]
    log_f = ["F_购买频次", "M_消费金额", "客单价", "小类购买数", "复购紧迫度均值"]
    Xdf = cust[feats].copy()
    for c in log_f:
        Xdf[c] = np.log1p(Xdf[c].clip(lower=0))
    Xs = StandardScaler().fit_transform(Xdf.values)
    ref = GaussianMixture(k, covariance_type="full", random_state=RNG,
                          n_init=3, reg_covar=1e-4).fit(Xs).predict(Xs)
    n = len(Xs); rng = np.random.default_rng(RNG)
    aris = []
    for b in range(n_boot):
        idx = rng.choice(n, n, replace=True)
        lab_b = GaussianMixture(k, covariance_type="full", random_state=b,
                                n_init=1, reg_covar=1e-4).fit(Xs[idx]).predict(Xs)
        aris.append(adjusted_rand_score(ref, lab_b))
    return np.array(aris)


def main():
    set_style()
    df = load_clean()

    # G 价格弹性
    el = price_elasticity(df)
    save_csv(el, "price_elasticity.csv")
    print("=== 需求价格弹性（DML 去偏）===")
    print(el[["范围", "价格弹性", "95%CI下", "95%CI上", "弹性类型"]].to_string(index=False))

    # C1 规则显著性
    sig = rule_significance(df)
    save_csv(sig, "rule_significance.csv")
    n_sig = (sig["是否显著"] == "显著").sum()
    print(f"\n=== 规则显著性: {n_sig}/{len(sig)} 条通过 Bonferroni 校正(α=0.05/{len(sig)}) ===")
    print(sig.head(8)[["前项", "后项", "提升度", "卡方", "p值", "是否显著"]].to_string(index=False))

    # C2 聚类稳定性
    aris = cluster_stability()
    stab = pd.DataFrame({"指标": ["平均ARI", "ARI标准差", "最小ARI", "bootstrap次数"],
                         "数值": [round(aris.mean(), 4), round(aris.std(), 4),
                                round(aris.min(), 4), len(aris)]})
    save_csv(stab, "cluster_stability.csv")
    print(f"\n=== 聚类稳定性: 平均 ARI={aris.mean():.3f} ± {aris.std():.3f} ===")

    _plots(el, sig, aris)
    return el, sig, stab


def _plots(el, sig, aris):
    # 价格弹性误差棒图
    e = el.copy()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    y = np.arange(len(e))
    colors = [PALETTE[1] if v == "整体" else PALETTE[0] for v in e["范围"]]
    ax.errorbar(e["价格弹性"], y,
                xerr=[e["价格弹性"] - e["95%CI下"], e["95%CI上"] - e["价格弹性"]],
                fmt="o", color="#333", ecolor="#888", capsize=4, markersize=6)
    for i, c in enumerate(colors):
        ax.plot(e["价格弹性"].iloc[i], y[i], "o", color=c, markersize=8)
    ax.axvline(-1, color=PALETTE[1], ls=":", lw=1.3, label="单位弹性 (-1)")
    ax.axvline(0, color="#C82423", ls="--", lw=1.2, label="零弹性")
    ax.set_yticks(y); ax.set_yticklabels(e["范围"], fontsize=9)
    ax.set_xlabel("价格弹性 ε = dlnQ/dlnP"); ax.legend(fontsize=9)
    savefig(fig, "el_价格弹性.png")

    # 规则显著性：lift vs chi2，显著着色
    fig, ax = plt.subplots(figsize=(8, 5.5))
    sigm = sig["是否显著"] == "显著"
    ax.scatter(sig.loc[sigm, "提升度"], sig.loc[sigm, "卡方"], s=50,
               color=PALETTE[3], edgecolors="#333", label="显著", zorder=3)
    ax.scatter(sig.loc[~sigm, "提升度"], sig.loc[~sigm, "卡方"], s=40,
               color="#bbb", edgecolors="#666", label="不显著")
    ax.set_yscale("log")
    ax.set_xlabel("提升度 lift"); ax.set_ylabel("卡方统计量 (log)"); ax.legend()
    savefig(fig, "el_规则显著性.png")

    # 聚类稳定性：ARI 分布箱线+散点
    fig, ax = plt.subplots(figsize=(6, 5.5))
    bp = ax.boxplot([aris], widths=0.5, patch_artist=True,
                    medianprops=dict(color=PALETTE[1], lw=2))
    bp["boxes"][0].set(facecolor=PALETTE[0], alpha=0.5)
    ax.scatter(np.random.normal(1, 0.04, len(aris)), aris, s=28,
               color=PALETTE[0], edgecolors="#333", alpha=0.7, zorder=3)
    ax.set_xticks([1]); ax.set_xticklabels(["GMM(k=7)"])
    ax.set_ylabel("调整兰德指数 ARI (bootstrap vs 参考)")
    ax.set_ylim(0, 1)
    savefig(fig, "el_聚类稳定性.png")


if __name__ == "__main__":
    main()
