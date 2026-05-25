# -*- coding: utf-8 -*-
"""
深化模块 B：Uplift 建模 + 个性化发券名单
在 §11.3 DML 群体级 CATE 基础上，做个体级处理效应(ITE)估计，输出"该给谁发券"。

方法：DR-learner（双重稳健，AIPW 伪结果，与 §11.3 DML 自洽）
  交叉拟合 μ0=E[Y|T=0,X], μ1=E[Y|T=1,X], 倾向 e=P(T=1|X)
  AIPW 伪结果 ψ = μ1−μ0 + T(Y−μ1)/e − (1−T)(Y−μ0)/(1−e)
  τ(X)=E[ψ|X] (LightGBM)；mean(ψ)≈DML 的 ATE
  （相比 T-learner 无外推偏差、相比 R-learner 伪结果有界稳定，是异质效应估计的稳健选择）
评估：Qini/AUUC 提升曲线（观测性数据，已用丰富混淆变量去偏；非 RCT，给出说明）。
策略：uplift>0 发券（边际增收），uplift<0 改用权益/不打折（避免毁利）。

产出：
  output/csvs/coupon_targeting_list.csv     发券名单（顾客级 uplift + 决策）
  output/csvs/uplift_segment_summary.csv     各群体 uplift 汇总
  output/figures/up_Qini提升曲线.png
  output/figures/up_群体uplift分布.png
  output/pkls/uplift_models.pkl
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split, KFold
from sklearn.base import clone
from lightgbm import LGBMRegressor, LGBMClassifier

from config import load_clean, save_csv, set_style, savefig, save_pkl, PALETTE, CSV_DIR

RNG = 42


def build_design(df):
    pos = df[df["is_return"] == 0].copy()
    cust = pd.read_csv(f"{CSV_DIR}/customer_profile.csv", encoding="utf-8-sig", dtype={"user_id": str})
    seg = pd.read_csv(f"{CSV_DIR}/customer_segments_hdbscan.csv", encoding="utf-8-sig", dtype={"user_id": str})
    pos = pos.merge(cust[["user_id", "M_消费金额", "F_购买频次", "促销敏感度", "类目熵",
                          "偏好价格分位"]], on="user_id", how="left")
    pos = pos.merge(seg[["user_id", "segment"]], on="user_id", how="left")
    ip = pos.groupby(["cat_l3_code", "item_id"])["unit_price"].mean().reset_index()
    ip["price_rank"] = ip.groupby("cat_l3_code")["unit_price"].rank(pct=True)
    pos = pos.merge(ip[["item_id", "price_rank"]], on="item_id", how="left")
    pos["price_rank"] = pos["price_rank"].fillna(0.5)
    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    cat_oh = ohe.fit_transform(pos[["cat_l1_name"]])
    num = pos[["unit_price", "price_rank", "weekday", "is_weekend", "sale_month",
               "M_消费金额", "F_购买频次", "促销敏感度", "类目熵", "偏好价格分位"]].fillna(0).values
    X = np.hstack([num, cat_oh])
    T = pos["is_promo"].values.astype(int)
    Y = pos["amount"].values.astype(float)
    return pos, X, T, Y


def _reg():
    return LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=31,
                         subsample=0.8, colsample_bytree=0.8, min_child_samples=40,
                         verbose=-1, n_jobs=-1)


def _clf():
    return LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                          subsample=0.8, colsample_bytree=0.8, min_child_samples=40,
                          verbose=-1, n_jobs=-1)


def dr_learner(X, T, Y, n_folds=5, e_clip=(0.02, 0.98)):
    """DR-learner（双重稳健 AIPW）：交叉拟合 μ0,μ1,e → AIPW 伪结果 ψ → 拟合 τ(X)。"""
    n = len(Y)
    mu0 = np.zeros(n); mu1 = np.zeros(n); e = np.zeros(n)
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=RNG)
    for tr, te in kf.split(X):
        Xt, Tt, Yt = X[tr], T[tr], Y[tr]
        m1 = clone(_reg()).fit(Xt[Tt == 1], Yt[Tt == 1])
        m0 = clone(_reg()).fit(Xt[Tt == 0], Yt[Tt == 0])
        ep = clone(_clf()).fit(Xt, Tt)
        mu1[te] = m1.predict(X[te]); mu0[te] = m0.predict(X[te])
        e[te] = np.clip(ep.predict_proba(X[te])[:, 1], *e_clip)
    psi = (mu1 - mu0) + T * (Y - mu1) / e - (1 - T) * (Y - mu0) / (1 - e)
    tau_model = _reg()
    tau_model.fit(X, psi)
    ite = tau_model.predict(X)
    return tau_model, ite, psi


def uplift_curve(ite, T, Y, n_bins=20):
    """观测性 uplift 曲线（连续结果）：按预测 ITE 降序，累计
    V(k)=ΣY_t(top-k) − ΣY_c(top-k)·(N_t,k/N_c,k)，AUUC=曲线下面积(相对随机)。"""
    order = np.argsort(-ite)
    T, Y = T[order], Y[order]
    n = len(T)
    fracs = np.linspace(1.0 / n_bins, 1.0, n_bins)
    xs, ys = [0.0], [0.0]
    for f in fracs:
        k = int(f * n)
        Tt, Yt = T[:k], Y[:k]
        nt = max((Tt == 1).sum(), 1); nc = max((Tt == 0).sum(), 1)
        v = Yt[Tt == 1].sum() - Yt[Tt == 0].sum() * (nt / nc)
        xs.append(f); ys.append(v)
    # 随机基线：总体 uplift 按比例
    total = ys[-1]
    rand = [total * x for x in xs]
    auuc = np.trapz(ys, xs); auuc_rand = np.trapz(rand, xs)
    return np.array(xs), np.array(ys), np.array(rand), auuc, auuc_rand


def main():
    set_style()
    df = load_clean()
    pos, X, T, Y = build_design(df)
    print(f"Uplift 样本(交易级): {X.shape}, 促销占比 {T.mean():.3f}")

    # DR-learner 全样本交叉拟合 ITE
    tau_model, ite_all, psi = dr_learner(X, T, Y)
    print(f"AIPW 估计 ATE = {psi.mean():.3f} 元/笔（应与 §11.3 DML 的 -2.5 接近）")
    # Qini 评估：在 30% 留出集上（用全样本训练的 τ 仅用于排序，评估仍按观测结果）
    idx = np.arange(len(T))
    _, te = train_test_split(idx, test_size=0.3, random_state=RNG, stratify=T)
    xs, ys, rand, auuc, auuc_rand = uplift_curve(ite_all[te], T[te], Y[te])
    lift_ratio = auuc / (auuc_rand + 1e-9)
    print(f"AUUC={auuc:.1f}  随机基线={auuc_rand:.1f}  提升比={lift_ratio:.2f}x")

    # 顾客级 uplift（对全样本 ITE 聚合到顾客）
    pos = pos.assign(ite=ite_all)
    cust_uplift = pos.groupby("user_id").agg(
        预测uplift=("ite", "mean"), 交易数=("ite", "size"),
        segment=("segment", "first"), 历史促销金额占比=("is_promo", "mean")).reset_index()
    cust_uplift = cust_uplift.sort_values("预测uplift", ascending=False)
    cust_uplift["发券决策"] = np.where(cust_uplift["预测uplift"] > 0, "发券", "权益/不打折")
    cust_uplift["uplift排名"] = range(1, len(cust_uplift) + 1)
    save_csv(cust_uplift.round(3), "coupon_targeting_list.csv")

    n_coupon = int((cust_uplift["预测uplift"] > 0).sum())
    print(f"发券名单: {n_coupon} 人 (uplift>0) / 共 {len(cust_uplift)} 人")
    print("Top5 应发券顾客:")
    print(cust_uplift.head(5)[["user_id", "segment", "预测uplift", "发券决策"]].to_string(index=False))

    # 各群体 uplift 汇总（与 DML CATE 互证）
    seg_sum = cust_uplift.groupby("segment").agg(
        人数=("user_id", "size"), 平均uplift=("预测uplift", "mean"),
        应发券人数=("发券决策", lambda s: (s == "发券").sum())).reset_index()
    seg_sum["应发券比例"] = (seg_sum["应发券人数"] / seg_sum["人数"]).round(3)
    seg_sum = seg_sum.sort_values("平均uplift", ascending=False)
    save_csv(seg_sum.round(3), "uplift_segment_summary.csv")
    print("\n各群体 uplift:")
    print(seg_sum.round(3).to_string(index=False))

    save_pkl({"tau_model": tau_model}, "uplift_models.pkl")
    _plots(xs, ys, rand, auuc, lift_ratio, cust_uplift, seg_sum)
    return cust_uplift, seg_sum


def _plots(xs, ys, rand, auuc, lift_ratio, cust_uplift, seg_sum):
    # Qini/uplift 提升曲线
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.plot(xs, ys, color=PALETTE[1], lw=2.2, marker="o", markersize=4,
            markerfacecolor="white", label=f"DR-learner (AUUC={auuc:.0f}, {lift_ratio:.2f}×随机)")
    ax.plot(xs, rand, color="#999999", ls="--", lw=1.5, label="随机发券基线")
    ax.fill_between(xs, rand, ys, where=(np.array(ys) >= np.array(rand)),
                    color=PALETTE[1], alpha=0.12)
    ax.set_xlabel("发券人群比例（按预测 uplift 降序）")
    ax.set_ylabel("累计增量销售额 (元)")
    ax.legend()
    savefig(fig, "up_Qini提升曲线.png")

    # 群体 uplift 分布（条形，正负着色）
    s = seg_sum.sort_values("平均uplift")
    colors = [PALETTE[3] if v > 0 else PALETTE[1] for v in s["平均uplift"]]
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh(s["segment"], s["平均uplift"], color=colors, edgecolor="white")
    ax.axvline(0, color="#333", lw=1)
    ax.set_xlabel("平均预测 uplift (元/笔，促销 vs 非促销)")
    savefig(fig, "up_群体uplift分布.png")


if __name__ == "__main__":
    main()
