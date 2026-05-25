# -*- coding: utf-8 -*-
"""
验证模块 MC：蒙特卡洛合成数据 → 全流程可还原性检验
思路：构造具有【已知真值】的生成过程（5 类顾客画像 + 注入的促销因果效应 β + 价格弹性 ε，
      且促销分配受类目/价格混淆），让本项目的核心方法去"盲跑"，检验能否还原真值：
  (1) 分群：GMM 能否还原已知顾客类别 → 调整兰德指数 ARI
  (2) 因果：DML 能否还原注入的促销效应 β（对比朴素估计的偏差）
  (3) 弹性：DML 能否还原注入的价格弹性 ε
多次蒙特卡洛重复，报告还原指标的分布。

产出：
  output/csvs/montecarlo_validation.csv     各次重复的还原指标
  output/csvs/montecarlo_summary.csv         汇总(均值±std)
  output/figures/mc_分群还原ARI.png
  output/figures/mc_促销效应还原.png
  output/figures/mc_价格弹性还原.png
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score
from lightgbm import LGBMRegressor, LGBMClassifier

from config import save_csv, set_style, savefig, PALETTE
from causal_dml import dml_partial_linear, naive_diff

# ----- 已知真值 -----
TRUE_BETA_PROMO = 0.40     # 促销对 log(销量) 的真实因果效应
TRUE_ELASTICITY = -0.60    # 真实价格弹性 dlnQ/dlnP
N_CUST = 1500
N_CAT = 6
PERIOD = 120
# 5 类顾客原型: (购买率λ, 客单对数均值, 品类偏好集中度, 主力品类)
# 各原型赋予可区分的频次/客单 + 不同主力品类，模拟"存在真实结构"的场景
SEGMENTS = [
    dict(name="高频全品类", lam=22, spend_mu=3.4, conc=0.5),
    dict(name="生鲜高频", lam=16, spend_mu=2.6, conc=3.0, focus=0),
    dict(name="粮油囤货", lam=7,  spend_mu=3.2, conc=3.0, focus=3),
    dict(name="低频低额", lam=3,  spend_mu=2.0, conc=0.6),
    dict(name="高客单低频", lam=4, spend_mu=4.2, conc=3.0, focus=4),
]
SEG_PROPS = [0.18, 0.16, 0.24, 0.30, 0.12]
CAT_BASE_PRICE = np.array([2.0, 5.0, 8.0, 12.0, 20.0, 4.0])
CAT_BASE_QTY = np.array([1.4, 0.6, 0.5, 0.4, 0.3, 1.0])   # 类目基线 log 销量偏移用
PROMO_CAT_BIAS = np.array([-1.5, 0.3, 0.8, 1.0, -0.5, 0.2])  # 类目促销倾向（混淆源）


def simulate(seed):
    rng = np.random.default_rng(seed)
    seg_ids = rng.choice(len(SEGMENTS), size=N_CUST, p=SEG_PROPS)
    # 每类的品类偏好向量
    seg_prefs = []
    for s in SEGMENTS:
        base = np.ones(N_CAT)
        if "focus" in s:
            base[s["focus"]] += 4.0
        pref = rng.dirichlet(base * s["conc"] + 0.3)
        seg_prefs.append(pref)
    rows = []
    for u in range(N_CUST):
        s = seg_ids[u]; sp = SEGMENTS[s]
        n_occ = rng.poisson(sp["lam"])
        for _ in range(n_occ):
            day = rng.integers(0, PERIOD)
            c = rng.choice(N_CAT, p=seg_prefs[s])
            price = CAT_BASE_PRICE[c] * np.exp(rng.normal(0, 0.3))
            logp = np.log(price)
            # 促销分配：受类目与价格混淆（便宜+特定类目更易促销）
            promo_logit = PROMO_CAT_BIAS[c] - 0.6 * (logp - np.log(CAT_BASE_PRICE[c])) - 0.5
            promo = int(rng.uniform() < 1 / (1 + np.exp(-promo_logit)))
            # 真实结构方程：logQ = 类目基线 + ε·logP + β·promo + 噪声
            logq = (CAT_BASE_QTY[c] + TRUE_ELASTICITY * (logp - np.log(CAT_BASE_PRICE[c]))
                    + TRUE_BETA_PROMO * promo + rng.normal(0, 0.4))
            qty = np.exp(logq)
            amount = qty * price * (0.7 if promo else 1.0)  # 促销价折扣体现在金额
            rows.append((u, s, day, c, price, logp, promo, qty, np.log(qty), amount))
    tx = pd.DataFrame(rows, columns=["user", "seg", "day", "cat", "price", "logP",
                                     "promo", "qty", "logQ", "amount"])
    return tx, seg_ids


def customer_features(tx):
    g = tx.groupby("user")
    feat = pd.DataFrame(index=range(N_CUST))
    feat["freq"] = g.size().reindex(feat.index).fillna(0)
    feat["spend"] = g["amount"].sum().reindex(feat.index).fillna(0)
    feat["avg"] = (feat["spend"] / feat["freq"].clip(lower=1))
    feat["promo_share"] = g["promo"].mean().reindex(feat.index).fillna(0)
    catsh = tx.pivot_table(index="user", columns="cat", values="amount",
                           aggfunc="sum", fill_value=0)
    catsh = catsh.div(catsh.sum(axis=1) + 1e-9, axis=0).reindex(feat.index).fillna(0)
    catsh.columns = [f"cat{c}" for c in catsh.columns]
    feat = pd.concat([feat, catsh], axis=1)
    feat["logfreq"] = np.log1p(feat["freq"])
    feat["logspend"] = np.log1p(feat["spend"])
    return feat.fillna(0)


def one_run(seed):
    tx, seg_true = simulate(seed)
    # 只保留有购买的顾客做分群
    feat = customer_features(tx)
    active = feat["freq"] > 0
    cols = ["logfreq", "logspend", "avg", "promo_share"] + [f"cat{c}" for c in range(N_CAT)]
    Xs = StandardScaler().fit_transform(feat.loc[active, cols].values)
    gm = GaussianMixture(len(SEGMENTS), covariance_type="full", random_state=seed,
                         n_init=3, reg_covar=1e-4).fit(Xs)
    lab = gm.predict(Xs)
    seg_act = seg_true[active.values]
    ari = adjusted_rand_score(seg_act, lab)
    # 高活跃顾客(≥8笔)的还原——信号充足时的方法上限
    hi = feat.loc[active, "freq"].values >= 8
    ari_hi = adjusted_rand_score(seg_act[hi], lab[hi]) if hi.sum() > 20 else np.nan

    # DML 促销效应：T=promo, Y=logQ, X=[类目 one-hot, logP]
    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    catoh = ohe.fit_transform(tx[["cat"]])
    Xp = np.hstack([catoh, tx[["logP"]].values])
    lreg = LGBMRegressor(n_estimators=150, learning_rate=0.08, num_leaves=31,
                         min_child_samples=40, verbose=-1, n_jobs=-1)
    lclf = LGBMClassifier(n_estimators=150, learning_rate=0.08, num_leaves=31,
                          min_child_samples=40, verbose=-1, n_jobs=-1)
    res_p = dml_partial_linear(Xp, tx["promo"].values, tx["logQ"].values, n_folds=3,
                               model_y=lreg, model_t=lclf, discrete_treatment=True)
    naive_p = naive_diff(tx["promo"].values, tx["logQ"].values)

    # DML 弹性：T=logP, Y=logQ, X=[类目 one-hot, promo]
    Xe = np.hstack([catoh, tx[["promo"]].values])
    res_e = dml_partial_linear(Xe, tx["logP"].values, tx["logQ"].values, n_folds=3,
                               model_y=LGBMRegressor(n_estimators=150, learning_rate=0.08,
                                                     num_leaves=31, min_child_samples=40,
                                                     verbose=-1, n_jobs=-1),
                               model_t=LGBMRegressor(n_estimators=150, learning_rate=0.08,
                                                     num_leaves=31, min_child_samples=40,
                                                     verbose=-1, n_jobs=-1),
                               discrete_treatment=False)
    return dict(ARI=ari, ARI高活跃=ari_hi, DML促销=res_p["theta"], 朴素促销=naive_p,
                DML弹性=res_e["theta"])


def main():
    set_style()
    R = 15
    print(f"蒙特卡洛重复 {R} 次 | 真值: β_promo={TRUE_BETA_PROMO}, ε={TRUE_ELASTICITY}")
    recs = []
    for r in range(R):
        recs.append(one_run(1000 + r))
        if (r + 1) % 5 == 0:
            print(f"  完成 {r+1}/{R}")
    res = pd.DataFrame(recs)
    save_csv(res.round(4), "montecarlo_validation.csv")

    summ = pd.DataFrame({
        "指标": ["分群 ARI(全体)", "分群 ARI(高活跃≥8笔)", "DML 促销效应", "朴素 促销效应", "DML 价格弹性"],
        "真值": ["—", "—", TRUE_BETA_PROMO, f"(混淆,真值仍{TRUE_BETA_PROMO})", TRUE_ELASTICITY],
        "均值": [res["ARI"].mean(), res["ARI高活跃"].mean(), res["DML促销"].mean(),
               res["朴素促销"].mean(), res["DML弹性"].mean()],
        "标准差": [res["ARI"].std(), res["ARI高活跃"].std(), res["DML促销"].std(),
                res["朴素促销"].std(), res["DML弹性"].std()],
    })
    summ["均值"] = summ["均值"].round(4); summ["标准差"] = summ["标准差"].round(4)
    save_csv(summ, "montecarlo_summary.csv")
    print("\n=== 还原性汇总 ===")
    print(summ.to_string(index=False))
    print(f"\nDML 促销效应偏差={res['DML促销'].mean()-TRUE_BETA_PROMO:+.3f}, "
          f"朴素偏差={res['朴素促销'].mean()-TRUE_BETA_PROMO:+.3f}")
    print(f"DML 弹性偏差={res['DML弹性'].mean()-TRUE_ELASTICITY:+.3f}")

    _plots(res)
    return res, summ


def _plots(res):
    # 分群 ARI 分布（全体 vs 高活跃）
    fig, ax = plt.subplots(figsize=(7, 5))
    data = [res["ARI"].dropna(), res["ARI高活跃"].dropna()]
    bp = ax.boxplot(data, widths=0.55, patch_artist=True,
                    medianprops=dict(color="#333", lw=2),
                    labels=["全体顾客", "高活跃顾客(≥8笔)"])
    for b, c in zip(bp["boxes"], [PALETTE[0], PALETTE[3]]):
        b.set(facecolor=c, alpha=0.55)
    for i, d in enumerate(data, 1):
        ax.scatter(np.random.normal(i, 0.04, len(d)), d, s=26,
                   color="#333", alpha=0.6, zorder=3)
    ax.axhline(0.6, color=PALETTE[1], ls="--", lw=1.2, label="良好阈值 0.6")
    ax.set_ylim(0, 1)
    ax.set_ylabel("调整兰德指数 ARI（还原 vs 真实类别）"); ax.legend()
    savefig(fig, "mc_分群还原ARI.png")

    # 促销效应还原：DML vs 朴素 vs 真值
    fig, ax = plt.subplots(figsize=(8, 5))
    parts = ax.boxplot([res["朴素促销"], res["DML促销"]], widths=0.5, patch_artist=True,
                       medianprops=dict(color="#333", lw=2), labels=["朴素估计", "DML 估计"])
    for b, c in zip(parts["boxes"], [PALETTE[3], PALETTE[0]]):
        b.set(facecolor=c, alpha=0.55)
    ax.axhline(TRUE_BETA_PROMO, color=PALETTE[1], ls="--", lw=1.6,
               label=f"真值 β={TRUE_BETA_PROMO}")
    ax.set_ylabel("促销对 log(销量) 的估计效应"); ax.legend()
    savefig(fig, "mc_促销效应还原.png")

    # 价格弹性还原
    fig, ax = plt.subplots(figsize=(6, 5))
    bp = ax.boxplot([res["DML弹性"]], widths=0.5, patch_artist=True,
                    medianprops=dict(color="#333", lw=2), labels=["DML 估计"])
    bp["boxes"][0].set(facecolor=PALETTE[2], alpha=0.6)
    ax.scatter(np.random.normal(1, 0.04, len(res)), res["DML弹性"], s=30,
               color=PALETTE[2], edgecolors="#333", alpha=0.7, zorder=3)
    ax.axhline(TRUE_ELASTICITY, color=PALETTE[1], ls="--", lw=1.6,
               label=f"真值 ε={TRUE_ELASTICITY}")
    ax.set_ylabel("价格弹性估计"); ax.legend()
    savefig(fig, "mc_价格弹性还原.png")


if __name__ == "__main__":
    main()
