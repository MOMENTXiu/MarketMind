# -*- coding: utf-8 -*-
"""
广度模块 E：销售时间序列分析与预测
日销售额：季节分解（周周期）+ ACF/PACF + Holt-Winters 指数平滑预测（回测）。
对比季节朴素基线，评估 MAPE/RMSE。

产出：
  output/csvs/timeseries_forecast.csv      回测预测 vs 实际
  output/csvs/timeseries_metrics.csv        预测精度对比
  output/figures/ts_季节分解.png
  output/figures/ts_自相关偏自相关.png
  output/figures/ts_预测回测.png
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from config import load_clean, save_csv, set_style, savefig, PALETTE

H = 14  # 预测/回测步长（天）


def main():
    set_style()
    df = load_clean()
    pos = df[df["is_return"] == 0]
    daily = pos.groupby("sale_date")["amount"].sum().asfreq("D").fillna(0.0)
    print(f"日序列长度 {len(daily)} 天: {daily.index.min().date()} ~ {daily.index.max().date()}")

    # --- 季节分解（周周期=7）---
    dec = seasonal_decompose(daily, model="additive", period=7)

    # --- 训练/回测切分 ---
    train, test = daily.iloc[:-H], daily.iloc[-H:]

    # Holt-Winters（加性趋势 + 周季节）
    hw = ExponentialSmoothing(train, trend="add", seasonal="add",
                              seasonal_periods=7, initialization_method="estimated").fit()
    fc_hw = hw.forecast(H)
    # 季节朴素基线 y[t-7]
    fc_naive = pd.Series([train.iloc[-7 + (i % 7)] for i in range(H)], index=test.index)

    def metrics(actual, pred):
        a, p = actual.values, np.asarray(pred)
        mae = np.mean(np.abs(a - p))
        rmse = np.sqrt(np.mean((a - p) ** 2))
        mask = a > 1
        mape = np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100
        return mae, rmse, mape

    rows = []
    for name, fc in [("Holt-Winters", fc_hw), ("季节朴素基线", fc_naive)]:
        mae, rmse, mape = metrics(test, fc)
        rows.append({"模型": name, "MAE": round(mae, 1), "RMSE": round(rmse, 1),
                     "MAPE(%)": round(mape, 2)})
    met = pd.DataFrame(rows)
    save_csv(met, "timeseries_metrics.csv")
    print(met.to_string(index=False))

    fc_df = pd.DataFrame({"日期": test.index, "实际": test.values.round(1),
                          "HoltWinters预测": fc_hw.values.round(1),
                          "季节朴素预测": fc_naive.values.round(1)})
    save_csv(fc_df, "timeseries_forecast.csv")

    _plots(daily, dec, train, test, fc_hw, fc_naive)
    return met


def _plots(daily, dec, train, test, fc_hw, fc_naive):
    # 季节分解 4 面板
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for ax, comp, lab, col in zip(
            axes, [dec.observed, dec.trend, dec.seasonal, dec.resid],
            ["原始", "趋势", "周季节", "残差"], PALETTE[:4]):
        ax.plot(comp.index, comp.values, color=col, lw=1.4)
        ax.set_ylabel(lab)
        ax.grid(True, alpha=0.4)
    axes[-1].set_xlabel("日期")
    fig.autofmt_xdate()
    savefig(fig, "ts_季节分解.png")

    # ACF / PACF
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    plot_acf(daily.values, ax=axes[0], lags=30, color=PALETTE[0], vlines_kwargs={"colors": PALETTE[0]})
    plot_pacf(daily.values, ax=axes[1], lags=30, method="ywm", color=PALETTE[1], vlines_kwargs={"colors": PALETTE[1]})
    axes[0].set_title(""); axes[1].set_title("")
    axes[0].set_xlabel("滞后阶数"); axes[0].set_ylabel("自相关 ACF")
    axes[1].set_xlabel("滞后阶数"); axes[1].set_ylabel("偏自相关 PACF")
    savefig(fig, "ts_自相关偏自相关.png")

    # 回测预测
    fig, ax = plt.subplots(figsize=(11, 5))
    hist = train.iloc[-35:]
    ax.plot(hist.index, hist.values, color="#666", lw=1.4, label="历史")
    ax.plot(test.index, test.values, color=PALETTE[0], lw=2, marker="o",
            markersize=4, label="实际")
    ax.plot(test.index, fc_hw.values, color=PALETTE[1], lw=2, ls="--", marker="s",
            markersize=4, label="Holt-Winters 预测")
    ax.plot(test.index, fc_naive.values, color=PALETTE[3], lw=1.5, ls=":",
            marker="^", markersize=4, label="季节朴素基线")
    ax.axvline(test.index[0], color="#bbb", ls="--", lw=1)
    ax.set_xlabel("日期"); ax.set_ylabel("日销售金额 (元)"); ax.legend()
    fig.autofmt_xdate()
    savefig(fig, "ts_预测回测.png")


if __name__ == "__main__":
    main()
