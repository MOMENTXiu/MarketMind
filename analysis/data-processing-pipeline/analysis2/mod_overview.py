# -*- coding: utf-8 -*-
"""普适分析模块 1：描述性概览（销售/类目/时序/人口/促销）。按可用标准字段自适应。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import seasonal_decompose
from config_3 import savefig, save_csv, positive, PALETTE, SEQ_CMAP, BINARY_COLORS


def run(df, dataset, cap):
    pos = positive(df)
    out = {}
    has = lambda c: c in df.columns

    # ---- 概览统计 ----
    ov = {"记录数": len(df), "用户数": df["user_id"].nunique() if has("user_id") else None,
          "商品数": df["item_id"].nunique() if has("item_id") else None,
          "订单数": df["order_id"].nunique() if has("order_id") else None,
          "总销售额": round(pos["amount"].sum(), 2) if has("amount") else None,
          "退货率": round(df["is_return"].mean(), 4) if has("is_return") else None}
    if has("amount"):
        ov["客单价"] = round(pos["amount"].sum() / max(df["order_id"].nunique() if has("order_id") else len(pos), 1), 2)
    save_csv(pd.DataFrame([ov]).T.reset_index().rename(columns={"index": "指标", 0: "数值"}),
             dataset, "overview_summary.csv")
    out["overview"] = ov

    # ---- 类目贡献 + 帕累托 ----
    if has("cat_l1_name") and has("amount"):
        cs = pos.groupby("cat_l1_name")["amount"].sum().sort_values(ascending=False)
        cum = cs.cumsum() / cs.sum() * 100
        save_csv(cs.reset_index().rename(columns={"amount": "销售额"}), dataset, "overview_category.csv")
        n = min(len(cs), 15)
        fig, ax = plt.subplots(figsize=(max(7, n * 0.6), 5))
        ax.bar(range(n), cs.values[:n], color=PALETTE[0], edgecolor="white")
        ax.set_xticks(range(n)); ax.set_xticklabels(cs.index[:n], rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("销售额")
        ax2 = ax.twinx(); ax2.plot(range(n), cum.values[:n], color=PALETTE[1], marker="o", lw=2)
        ax2.set_ylabel("累计占比 (%)"); ax2.set_ylim(0, 105); ax2.grid(False)
        ax2.axhline(80, color="#999", ls="--", lw=1)
        savefig(fig, dataset, "overview_类目帕累托.png")
        out["top_category"] = cs.index[0]
        out["pareto_top20pct_share"] = round(cs.head(max(1, len(cs) // 5)).sum() / cs.sum(), 3)

    # ---- 时间趋势 + 季节分解 ----
    if has("sale_date") and has("amount"):
        daily = pos.groupby(pos["sale_date"].dt.normalize())["amount"].sum()
        span = (daily.index.max() - daily.index.min()).days
        fig, ax = plt.subplots(figsize=(11, 4.2))
        ax.plot(daily.index, daily.values, color=PALETTE[7], lw=0.8, alpha=0.5, label="日销售额")
        if len(daily) >= 14:
            ax.plot(daily.index, daily.rolling(min(30, len(daily) // 3), center=True).mean(),
                    color=PALETTE[1], lw=2.2, label="滚动均值")
        ax.set_xlabel("日期"); ax.set_ylabel("销售额"); ax.legend(); fig.autofmt_xdate()
        savefig(fig, dataset, "overview_时间趋势.png")
        # 季节分解（足够跨度时按月，否则按周）
        if span >= 120:
            monthly = pos.groupby(pos["sale_date"].dt.to_period("M"))["amount"].sum()
            monthly.index = monthly.index.to_timestamp()
            monthly = monthly.asfreq("MS").fillna(monthly.mean())
            period = 12 if len(monthly) >= 24 else max(2, len(monthly) // 2)
            if len(monthly) >= 2 * period:
                dec = seasonal_decompose(monthly, model="additive", period=period)
                _plot_decompose(dec, dataset)
                out["seasonal"] = True

    # ---- 人口统计（电商类数据）----
    if has("gender") or has("age"):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        if has("gender"):
            gc = df["gender"].value_counts()
            axes[0].pie(gc.values, labels=gc.index, autopct="%1.1f%%", startangle=90,
                        colors=PALETTE[:len(gc)], wedgeprops=dict(width=0.42, edgecolor="white"),
                        pctdistance=0.78)
            axes[0].set(aspect="equal")
        if has("age"):
            axes[1].hist(pd.to_numeric(df["age"], errors="coerce").dropna(), bins=30,
                         color=PALETTE[3], alpha=0.8, edgecolor="white")
            axes[1].set_xlabel("年龄"); axes[1].set_ylabel("人数")
        savefig(fig, dataset, "overview_人口分布.png")

    # ---- 促销/折扣使用 ----
    if has("is_promo") and has("amount"):
        g = pos.groupby("is_promo").agg(销售额=("amount", "sum"), 笔数=("amount", "size"))
        fig, ax = plt.subplots(figsize=(6.5, 4.5))
        lab = ["非促销", "促销"]
        vals = [g["销售额"].get(0, 0), g["销售额"].get(1, 0)]
        ax.bar(lab, vals, color=BINARY_COLORS, edgecolor="white", width=0.55)
        ax.set_ylabel("销售额")
        savefig(fig, dataset, "overview_促销对比.png")
        out["promo_share"] = round(pos[pos["is_promo"] == 1]["amount"].sum() / pos["amount"].sum(), 3)

    return out


def _plot_decompose(dec, dataset):
    fig, axes = plt.subplots(4, 1, figsize=(10, 8.5), sharex=True)
    for ax, comp, lab, col in zip(axes, [dec.observed, dec.trend, dec.seasonal, dec.resid],
                                  ["原始", "趋势", "季节", "残差"], PALETTE[:4]):
        ax.plot(comp.index, comp.values, color=col, lw=1.3); ax.set_ylabel(lab)
    axes[-1].set_xlabel("日期"); fig.autofmt_xdate()
    savefig(fig, dataset, "overview_季节分解.png")
