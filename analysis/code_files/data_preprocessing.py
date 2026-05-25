# -*- coding: utf-8 -*-
"""
阶段 1：数据预处理
输入：data/销售数据.csv (GBK)
输出：
    output/csvs/cleaned_sales_data.csv      清洗后明细
    output/csvs/数据质量报告.csv             逐项处理统计
    output/csvs/单位映射表.csv               单位归一映射
    output/figures/01_缺失率统计.png
    output/figures/06_促销非促销对比.png
    output/figures/07_顾客消费金额长尾分布.png
    output/figures/02_大类销售金额占比.png
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import (DATA_FILE, DATA_ENCODING, set_style, savefig, save_csv,
                    PALETTE, BINARY_COLORS, CLEAN_FILE)

RAW2INNER = {
    "顾客编号": "user_id", "大类编码": "cat_l1_code", "大类名称": "cat_l1_name",
    "中类编码": "cat_l2_code", "中类名称": "cat_l2_name", "小类编码": "cat_l3_code",
    "小类名称": "cat_l3_name", "销售日期": "sale_date", "销售月份": "sale_month",
    "商品编码": "item_id", "规格型号": "spec", "商品类型": "item_type", "单位": "unit",
    "销售数量": "quantity", "销售金额": "amount", "商品单价": "unit_price",
    "是否促销": "is_promo",
}

# 单位统一映射（详见 project_plan.md §3）
UNIT_MAP = {
    "千克": "千克", "KG": "千克", "kg": "千克", "Kg": "千克", "公斤": "千克", "散称": "千克",
    "袋": "袋", "d袋": "袋",
    "盒": "盒", "合": "盒",
    "副": "副", "付": "副",
    "代": "代",
}
UNIT_DIRTY = {"", "2", "0", "160g", "一般", "快", "装"}  # 脏值→未知单位


def normalize_unit(u):
    if pd.isna(u):
        return "未知单位"
    s = str(u).replace("　", "").strip()  # 去全角/半角空格
    if s in UNIT_DIRTY:
        return "未知单位"
    return UNIT_MAP.get(s, s if s else "未知单位")


def repair_shifted_rows(df_raw):
    """修复因规格型号含逗号导致整体右移一列的错位行。
    特征：是否促销 not in {是,否}。这些行 商品类型=='12g*8',单位=='一般',数量缺失。
    真实：规格='牛魔空版 12g*8',类型=一般商品,金额=9.9,单价=9.9,数量=金额/单价,促销=否。
    """
    mask = ~df_raw["是否促销"].isin(["是", "否"])
    n = int(mask.sum())
    if n == 0:
        return df_raw, 0
    idx = df_raw.index[mask]
    for i in idx:
        price = pd.to_numeric(df_raw.at[i, "商品单价"], errors="coerce")
        # 错位后：商品单价列实际存的是金额、是否促销列存的是单价
        amount = price                       # 9.9
        unit_price = pd.to_numeric(df_raw.at[i, "是否促销"], errors="coerce")  # 9.9
        spec = f"{df_raw.at[i,'规格型号']} {df_raw.at[i,'商品类型']}".strip()  # 牛魔空版 12g*8
        df_raw.at[i, "规格型号"] = spec
        df_raw.at[i, "商品类型"] = "一般商品"
        df_raw.at[i, "单位"] = "未知单位"
        df_raw.at[i, "销售金额"] = amount
        df_raw.at[i, "商品单价"] = unit_price
        df_raw.at[i, "销售数量"] = round(amount / unit_price, 4) if unit_price else 1.0
        df_raw.at[i, "是否促销"] = "否"
    return df_raw, n


def main():
    set_style()
    report = []  # (项目, 处理前/统计, 处理方式/结果)

    # 1. 载入
    raw = pd.read_csv(DATA_FILE, encoding=DATA_ENCODING)
    report.append(("原始记录数", len(raw), "—"))

    # 2. 修复错位行
    raw, n_shift = repair_shifted_rows(raw)
    report.append(("错位行修复", n_shift, "规格含逗号致右移，已按金额/单价还原数量"))

    # 3. 去重
    n0 = len(raw)
    raw = raw.drop_duplicates().reset_index(drop=True)
    report.append(("完全重复行去除", n0 - len(raw), f"剩余 {len(raw)}"))

    # 4. 重命名
    df = raw.rename(columns=RAW2INNER).copy()

    # 5. 类目编码补零成字符串（保持稳定主键）
    df["user_id"] = df["user_id"].astype(int).astype(str).str.zfill(4)
    df["item_id"] = df["item_id"].astype(str).str.strip()
    df["cat_l1_code"] = df["cat_l1_code"].astype(int).astype(str)
    df["cat_l2_code"] = df["cat_l2_code"].astype(int).astype(str)
    df["cat_l3_code"] = df["cat_l3_code"].astype(int).astype(str)

    # 6. 数值列
    for c in ["quantity", "amount", "unit_price"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # 7. 日期与时间特征（含非法日期订正，如非闰年 20250229 → 20250228）
    ds = df["sale_date"].astype(str)
    sale_date = pd.to_datetime(ds, format="%Y%m%d", errors="coerce")
    n_baddate = int(sale_date.isna().sum())
    if n_baddate:
        for i in df.index[sale_date.isna()]:
            y, m = int(ds[i][:4]), int(ds[i][4:6])
            last = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(1)
            sale_date.at[i] = last
    df["sale_date"] = sale_date
    report.append(("非法日期订正", n_baddate, "如非闰年2/29→当月最后一天"))
    df["sale_month"] = df["sale_month"].astype(int)
    df["weekday"] = df["sale_date"].dt.weekday            # 0=周一
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)
    df["week_of_year"] = df["sale_date"].dt.isocalendar().week.astype(int)
    report.append(("日期范围", f"{df['sale_date'].min().date()} ~ {df['sale_date'].max().date()}", "已派生 weekday/周末/周序"))

    # 8. 促销二值化
    df["is_promo"] = df["is_promo"].map({"是": 1, "否": 0}).fillna(0).astype(int)
    report.append(("促销记录占比", f"{df['is_promo'].mean():.4f}", f"促销 {int(df['is_promo'].sum())} 行"))

    # 9. 退货标记（数量<=0 或 金额<=0）
    df["is_return"] = ((df["quantity"] <= 0) | (df["amount"] <= 0)).astype(int)
    report.append(("退货/异常行标记", int(df["is_return"].sum()), "is_return=1，不计入正向购买"))

    # 10. 单位归一
    df["unit"] = df["unit"].map(normalize_unit)
    report.append(("单位归一后种类", df["unit"].nunique(), "千克/袋/盒/副等合并"))

    # 11. 规格填补
    spec_blank = (df["spec"].astype(str).str.strip() == "") | df["spec"].isna()
    df.loc[spec_blank, "spec"] = "未知规格"
    report.append(("规格空白填补", int(spec_blank.sum()), "→未知规格"))

    # 12. 单价填补（=0 或缺失）：同商品中位数→同小类中位数
    bad_price = (df["unit_price"].isna()) | (df["unit_price"] <= 0)
    if bad_price.any():
        item_med = df.loc[~bad_price].groupby("item_id")["unit_price"].median()
        l3_med = df.loc[~bad_price].groupby("cat_l3_code")["unit_price"].median()
        for i in df.index[bad_price]:
            v = item_med.get(df.at[i, "item_id"], np.nan)
            if pd.isna(v):
                v = l3_med.get(df.at[i, "cat_l3_code"], np.nan)
            if pd.isna(v):
                v = df.loc[~bad_price, "unit_price"].median()
            df.at[i, "unit_price"] = v
    report.append(("单价异常填补", int(bad_price.sum()), "同商品→同小类→全局中位数"))

    # 13. 缺失数量回填（极少数，用 金额/单价）
    miss_q = df["quantity"].isna()
    df.loc[miss_q, "quantity"] = (df.loc[miss_q, "amount"] / df.loc[miss_q, "unit_price"]).round(4)
    report.append(("数量缺失回填", int(miss_q.sum()), "金额/单价"))

    # ---- 保存清洗结果 ----
    cols = ["user_id", "cat_l1_code", "cat_l1_name", "cat_l2_code", "cat_l2_name",
            "cat_l3_code", "cat_l3_name", "sale_date", "sale_month", "item_id",
            "spec", "item_type", "unit", "quantity", "amount", "unit_price",
            "is_promo", "is_return", "weekday", "is_weekend", "week_of_year"]
    df = df[cols]
    df.to_csv(CLEAN_FILE, index=False, encoding="utf-8-sig")
    print(f"[CSV] {CLEAN_FILE}  shape={df.shape}")

    # 质量报告
    rep_df = pd.DataFrame(report, columns=["处理项目", "数值/统计", "说明"])
    save_csv(rep_df, "数据质量报告.csv")

    # 单位映射表
    um = (df.assign(原始=raw.rename(columns=RAW2INNER)["unit"].values if False else None))
    unit_tbl = pd.Series({**{k: v for k, v in UNIT_MAP.items()},
                          **{d: "未知单位" for d in UNIT_DIRTY if d}})
    unit_tbl = unit_tbl.reset_index()
    unit_tbl.columns = ["原始单位", "归一单位"]
    save_csv(unit_tbl, "单位映射表.csv")

    # ---- 关键统计供后续 ----
    print("\n=== 清洗后概览 ===")
    print("记录数:", len(df), "| 顾客:", df["user_id"].nunique(),
          "| 商品:", df["item_id"].nunique(), "| 正向购买:", int((df["is_return"] == 0).sum()))

    _plot_quality(raw.rename(columns=RAW2INNER), df)
    return df


def _plot_quality(raw_inner, df):
    # 图1：缺失率统计（用原始数据各列缺失/异常率）
    fields = ["quantity", "amount", "unit_price", "spec", "unit", "is_promo"]
    labels = ["销售数量", "销售金额", "商品单价", "规格型号", "单位", "是否促销"]
    raw_q = pd.to_numeric(raw_inner["quantity"], errors="coerce")
    raw_a = pd.to_numeric(raw_inner["amount"], errors="coerce")
    raw_p = pd.to_numeric(raw_inner["unit_price"], errors="coerce")
    rates = [
        raw_q.isna().mean() * 100,
        raw_a.isna().mean() * 100,
        ((raw_p.isna()) | (raw_p <= 0)).mean() * 100,
        (raw_inner["spec"].astype(str).str.strip() == "").mean() * 100,
        (raw_inner["unit"].astype(str).str.replace("　", "").str.strip() == "").mean() * 100,
        (~raw_inner["is_promo"].isin(["是", "否"])).mean() * 100,
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, rates, color=PALETTE[0], edgecolor="white", width=0.6)
    for b, r in zip(bars, rates):
        ax.text(b.get_x() + b.get_width() / 2, r + 0.01, f"{r:.3f}%",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("缺失/异常率 (%)")
    ax.set_ylim(0, max(rates) * 1.25 + 0.1)
    savefig(fig, "01_缺失率统计.png")

    # 图6：促销/非促销 销售额与笔数对比
    pos = df[df["is_return"] == 0]
    g = pos.groupby("is_promo").agg(销售额=("amount", "sum"), 笔数=("amount", "size"))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    xlab = ["非促销", "促销"]
    axes[0].bar(xlab, g["销售额"].reindex([0, 1]).values, color=BINARY_COLORS,
                edgecolor="white", width=0.55)
    axes[0].set_ylabel("销售金额合计 (元)")
    axes[1].bar(xlab, g["笔数"].reindex([0, 1]).values, color=BINARY_COLORS,
                edgecolor="white", width=0.55)
    axes[1].set_ylabel("销售笔数")
    savefig(fig, "06_促销非促销对比.png")

    # 图7：顾客消费金额长尾分布
    cust_amt = pos.groupby("user_id")["amount"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(np.arange(1, len(cust_amt) + 1), cust_amt.values,
            color=PALETTE[1], lw=1.6)
    ax.fill_between(np.arange(1, len(cust_amt) + 1), cust_amt.values,
                    color=PALETTE[1], alpha=0.15)
    ax.set_xlabel("顾客排名（按消费金额降序）")
    ax.set_ylabel("累计消费金额 (元)")
    ax.set_yscale("log")
    savefig(fig, "07_顾客消费金额长尾分布.png")

    # 图2：大类销售金额占比（环形图）
    l1 = pos.groupby("cat_l1_name")["amount"].sum().sort_values(ascending=False)
    top = l1.head(8)
    other = l1.iloc[8:].sum()
    if other > 0:
        top = pd.concat([top, pd.Series({"其它": other})])
    fig, ax = plt.subplots(figsize=(7, 6))
    wedges, _, _ = ax.pie(top.values, labels=top.index, autopct="%1.1f%%",
                          startangle=90, counterclock=False,
                          colors=(PALETTE * 2)[:len(top)],
                          wedgeprops=dict(width=0.42, edgecolor="white"),
                          pctdistance=0.78, textprops={"fontsize": 10})
    ax.set(aspect="equal")
    savefig(fig, "02_大类销售金额占比.png")


if __name__ == "__main__":
    main()
