# -*- coding: utf-8 -*-
"""普适分析模块 5：促销/折扣因果分析 + 利润分析。按可用字段自适应。
朴素均值差 vs DML 去偏因果效应（控制类目/价格/时间等混淆）。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import OneHotEncoder
from config_3 import savefig, save_csv, positive, dml_ate, PALETTE, BINARY_COLORS


def run(df, dataset, cap):
    pos = positive(df).copy()
    has = lambda c: c in pos.columns
    out = {}

    treat_col = "is_promo" if has("is_promo") else None
    if treat_col is None or not has("amount"):
        return {"status": "skipped", "reason": "缺 is_promo/amount"}

    # ---- 朴素对比 ----
    ap = pos[pos[treat_col] == 1]["amount"].mean()
    an = pos[pos[treat_col] == 0]["amount"].mean()
    naive = ap - an
    out["naive_diff"] = round(naive, 3)

    # ---- DML 去偏因果效应 ----
    # 混淆 X：类目(one-hot) + 单价 + 时间 + 数量
    Xparts, names = [], []
    cat_col = next((c for c in ["cat_l1_name", "cat_l3_name"] if has(c)), None)
    if cat_col:
        ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore", min_frequency=30)
        Xparts.append(ohe.fit_transform(pos[[cat_col]]))
    for c in ["unit_price", "quantity", "sale_month", "weekday"]:
        if has(c):
            Xparts.append(pos[[c]].fillna(0).values); names.append(c)
    theta = se = ci = None
    if Xparts:
        X = np.hstack(Xparts)
        T = pos[treat_col].values; Y = pos["amount"].values
        try:
            theta, se, ci = dml_ate(X, T, Y, n_folds=5, discrete_treatment=True)
            out["dml_ate"] = round(theta, 3); out["dml_ci"] = [round(ci[0], 3), round(ci[1], 3)]
            out["dml_significant"] = bool(ci[0] * ci[1] > 0)
        except Exception as e:
            out["dml_error"] = str(e)[:60]

    save_csv(pd.DataFrame([{"方法": "朴素均值差", "效应(元/笔)": round(naive, 3), "95%CI下": None, "95%CI上": None},
                           {"方法": "DML去偏ATE", "效应(元/笔)": round(theta, 3) if theta is not None else None,
                            "95%CI下": round(ci[0], 3) if ci else None,
                            "95%CI上": round(ci[1], 3) if ci else None}]),
             dataset, "promotion_effect.csv")

    # ---- 折扣/利润（若有）----
    if has("discount"):
        dd = pos.groupby(pd.cut(pos["discount"], [-0.01, 0, 0.2, 0.4, 1.0],
                                labels=["无", "0-0.2", "0.2-0.4", ">0.4"]),
                         observed=True)["amount"].mean()
        out["discount_levels"] = dd.round(2).to_dict()
    if has("profit"):
        out["total_profit"] = round(pos["profit"].sum(), 1)
        out["profit_margin"] = round(pos["profit"].sum() / pos["amount"].sum(), 4)

    _plots(pos, naive, theta, ci, dataset, has)
    return {"status": "ok", **out}


def _plots(pos, naive, theta, ci, dataset, has):
    # 促销 vs 非促销 笔均 + DML 对比
    fig, ax = plt.subplots(figsize=(8, 5))
    cats = ["朴素\n非促销均值", "朴素\n促销均值"]
    ax.bar(cats, [pos[pos.is_promo == 0]["amount"].mean(), pos[pos.is_promo == 1]["amount"].mean()],
           color=BINARY_COLORS, edgecolor="white", width=0.5)
    ax.set_ylabel("笔均销售额 (元)")
    if theta is not None:
        ax.axhline(0, color="#333", lw=0.8)
        txt = f"朴素差={naive:+.2f}\nDML去偏ATE={theta:+.2f}\n95%CI[{ci[0]:.2f},{ci[1]:.2f}]"
        ax.text(0.98, 0.95, txt, transform=ax.transAxes, ha="right", va="top", fontsize=10,
                bbox=dict(boxstyle="round", fc="white", ec="#888"))
    savefig(fig, dataset, "promotion_因果对比.png")

    if has("profit"):
        cp = pos.groupby("cat_l1_name")["profit"].sum().sort_values() if "cat_l1_name" in pos else None
        if cp is not None and len(cp) > 1:
            fig, ax = plt.subplots(figsize=(8, max(4, len(cp) * 0.4)))
            colors = [PALETTE[1] if v < 0 else PALETTE[3] for v in cp.values]
            ax.barh(cp.index, cp.values, color=colors, edgecolor="white")
            ax.axvline(0, color="#333", lw=1)
            ax.set_xlabel("利润合计")
            savefig(fig, dataset, "promotion_类目利润.png")
