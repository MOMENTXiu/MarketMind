# -*- coding: utf-8 -*-
"""
广度模块 F：顾客生命周期价值 CLV（BG/NBD + Gamma-Gamma）
- BG/NBD：基于 RFM 概率建模未来购买次数与"存活"概率（非合同制零售）；
- Gamma-Gamma：建模客单价；
- 二者结合 → 未来 90 天 CLV。
- 校准/留出验证：1–3 月校准，4 月留出，对比预测购买数 vs 实际。

产出：
  output/csvs/clv_predictions.csv     顾客 CLV + 未来购买/存活概率
  output/csvs/clv_validation.csv       校准-留出验证
  output/figures/clv_频次新近矩阵.png
  output/figures/clv_存活概率矩阵.png
  output/figures/clv_价值分布.png
  output/figures/clv_预测校准.png
  output/pkls/clv_models.pkl
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import (summary_data_from_transaction_data,
                             calibration_and_holdout_data)
from lifetimes.plotting import (plot_frequency_recency_matrix,
                                plot_probability_alive_matrix)

from config import load_clean, save_csv, set_style, savefig, save_pkl, PALETTE

OBS_END = pd.Timestamp("2025-04-30")
CAL_END = pd.Timestamp("2025-03-31")
FUTURE_DAYS = 90


def main():
    set_style()
    df = load_clean()
    pos = df[df["is_return"] == 0].copy()
    # 交易日志：同一顾客同一天合并为一次"购买"，金额求和
    tx = pos.groupby(["user_id", "sale_date"])["amount"].sum().reset_index()

    # ---- 全样本 RFM 汇总 ----
    summ = summary_data_from_transaction_data(
        tx, "user_id", "sale_date", monetary_value_col="amount",
        observation_period_end=OBS_END, freq="D")
    print(f"顾客数 {len(summ)}, 有复购(frequency>0) {int((summ['frequency']>0).sum())}")

    # ---- BG/NBD ----
    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(summ["frequency"], summ["recency"], summ["T"])
    summ["预测购买数_90天"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        FUTURE_DAYS, summ["frequency"], summ["recency"], summ["T"]).round(3)
    summ["存活概率"] = bgf.conditional_probability_alive(
        summ["frequency"], summ["recency"], summ["T"]).round(3)

    # ---- Gamma-Gamma（仅 frequency>0 且 monetary>0）----
    rpt = summ[(summ["frequency"] > 0) & (summ["monetary_value"] > 0)]
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(rpt["frequency"], rpt["monetary_value"])
    # 预测客单价（对全体；frequency=0 用整体均值兜底）
    summ["预测客单价"] = np.nan
    summ.loc[rpt.index, "预测客单价"] = ggf.conditional_expected_average_profit(
        rpt["frequency"], rpt["monetary_value"]).round(2)
    summ["预测客单价"] = summ["预测客单价"].fillna(summ.loc[rpt.index, "预测客单价"].mean())

    # ---- CLV（90 天，月贴现 1%）----
    clv = ggf.customer_lifetime_value(
        bgf, summ["frequency"], summ["recency"], summ["T"], summ["预测客单价"],
        time=3, freq="D", discount_rate=0.01)
    summ["CLV_90天"] = clv.round(2)
    out = summ.reset_index().rename(columns={
        "frequency": "历史复购次数", "recency": "新近度", "T": "客户年龄",
        "monetary_value": "历史客单价"})
    out = out.sort_values("CLV_90天", ascending=False)
    save_csv(out.round(3), "clv_predictions.csv")
    print("Top5 CLV 顾客:")
    print(out.head(5)[["user_id", "历史复购次数", "预测购买数_90天", "存活概率",
                       "预测客单价", "CLV_90天"]].to_string(index=False))
    print(f"CLV_90天 合计 {out['CLV_90天'].sum():.0f} 元，Top10% 顾客占 "
          f"{out['CLV_90天'].head(int(len(out)*0.1)).sum()/out['CLV_90天'].sum()*100:.1f}%")

    # ---- 校准/留出验证 ----
    cal_holdout = calibration_and_holdout_data(
        tx, "user_id", "sale_date", calibration_period_end=CAL_END,
        observation_period_end=OBS_END, freq="D")
    bgf_c = BetaGeoFitter(penalizer_coef=0.01)
    bgf_c.fit(cal_holdout["frequency_cal"], cal_holdout["recency_cal"], cal_holdout["T_cal"])
    holdout_days = (OBS_END - CAL_END).days
    cal_holdout["预测"] = bgf_c.conditional_expected_number_of_purchases_up_to_time(
        holdout_days, cal_holdout["frequency_cal"], cal_holdout["recency_cal"],
        cal_holdout["T_cal"])
    vmask = cal_holdout["frequency_holdout"].notna() & cal_holdout["预测"].notna()
    actual = cal_holdout.loc[vmask, "frequency_holdout"]
    pred = cal_holdout.loc[vmask, "预测"]
    mae = np.mean(np.abs(actual - pred))
    corr = pd.Series(actual.values).corr(pd.Series(pred.values))
    val = pd.DataFrame({"指标": ["留出期实际总购买", "预测总购买", "MAE", "预测-实际相关"],
                        "数值": [round(actual.sum(), 1), round(pred.sum(), 1),
                               round(mae, 4), round(corr, 4)]})
    save_csv(val, "clv_validation.csv")
    print(f"\n校准/留出验证: 预测总购买 {pred.sum():.0f} vs 实际 {actual.sum():.0f}, "
          f"MAE={mae:.3f}, 相关={corr:.3f}")

    # lifetimes 模型含 lambda 不可 pickle，改存参数
    save_pkl({"bgf_params": dict(bgf.params_), "ggf_params": dict(ggf.params_)},
             "clv_models.pkl")
    _plots(bgf, summ, out, cal_holdout)
    return out, val


def _plots(bgf, summ, out, cal_holdout):
    # 频次-新近矩阵
    plt.figure(figsize=(7, 5.5))
    plot_frequency_recency_matrix(bgf, cmap="YlGnBu")
    fig = plt.gcf(); ax = fig.axes[0]
    ax.set_title(""); ax.set_xlabel("新近度 (recency)"); ax.set_ylabel("历史购买频次")
    savefig(fig, "clv_频次新近矩阵.png")

    # 存活概率矩阵
    plt.figure(figsize=(7, 5.5))
    plot_probability_alive_matrix(bgf, cmap="YlOrRd")
    fig = plt.gcf(); ax = fig.axes[0]
    ax.set_title(""); ax.set_xlabel("历史购买频次"); ax.set_ylabel("新近度 (recency)")
    savefig(fig, "clv_存活概率矩阵.png")

    # CLV 分布（对数）
    fig, ax = plt.subplots(figsize=(8, 4.8))
    v = out["CLV_90天"].clip(lower=0)
    v = v[v > 0]
    ax.hist(np.log1p(v), bins=40, color=PALETTE[2], alpha=0.8, edgecolor="white")
    ax.set_xlabel("log(1 + 90天CLV)"); ax.set_ylabel("顾客数")
    savefig(fig, "clv_价值分布.png")

    # 预测校准散点（留出实际 vs 预测）
    fig, ax = plt.subplots(figsize=(6.5, 6))
    grp = cal_holdout.groupby(cal_holdout["frequency_cal"].clip(upper=10))
    gx = grp["预测"].mean(); gy = grp["frequency_holdout"].mean()
    ax.scatter(gx, gy, s=60, color=PALETTE[0], edgecolors="#333", zorder=3)
    lim = max(gx.max(), gy.max()) * 1.1
    ax.plot([0, lim], [0, lim], color="#C82423", ls="--", lw=1.3, label="理想 y=x")
    ax.set_xlabel("模型预测留出期购买数"); ax.set_ylabel("实际留出期购买数")
    ax.legend()
    savefig(fig, "clv_预测校准.png")


if __name__ == "__main__":
    main()
