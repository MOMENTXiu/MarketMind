# -*- coding: utf-8 -*-
"""
阶段 6：营销者侧决策模型（思路文档 §11、§14.4）
1) 群体价值识别     CRITIC-TOPSIS 排序 7 个顾客群体
2) 商品组合促销决策  FP-Growth/HUIM 候选 + TOPSIS BundleScore
3) 促销响应分析     朴素 PromoLift  vs  双重机器学习 DML 去偏因果效应(ATE/CATE)
4) 品类经营分析     贡献/增长/促销依赖/复购 → 五类经营策略

产出：
  output/csvs/segment_value_rank.csv
  output/csvs/bundle_strategy.csv
  output/csvs/promotion_response.csv
  output/csvs/category_operation_strategy.csv
  output/figures/16_群体推荐类目分布.png
  output/figures/mk_群体价值雷达.png
  output/figures/mk_促销因果效应.png       (DML ATE/CATE 误差棒/森林图)
  output/figures/mk_品类经营象限.png
  output/figures/14b_组合促销价值.png
  code_files/report_06_marketer.md
  code_files/marketer_report.md            （营销策略报告，思路 §12.2）
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import OneHotEncoder

from config import (load_clean, save_csv, set_style, savefig, topsis,
                    critic_weights, PALETTE, CSV_DIR, DOCS_DIR)
from causal_dml import dml_partial_linear, dml_group_cate, naive_diff


def load_inputs():
    df = load_clean()
    cust = pd.read_csv(f"{CSV_DIR}/customer_profile.csv", encoding="utf-8-sig", dtype={"user_id": str})
    seg = pd.read_csv(f"{CSV_DIR}/customer_segments_hdbscan.csv", encoding="utf-8-sig", dtype={"user_id": str})
    hui = pd.read_csv(f"{CSV_DIR}/high_utility_itemsets.csv", encoding="utf-8-sig")
    rules = pd.read_csv(f"{CSV_DIR}/association_rules_category.csv", encoding="utf-8-sig")
    return df, cust, seg, hui, rules


# ===========================================================================
# 1. 群体价值识别
# ===========================================================================
def segment_value(df, cust, seg):
    pos = df[df["is_return"] == 0]
    c = cust.merge(seg[["user_id", "segment"]], on="user_id", how="left")
    # 群体促销响应率（促销金额占比）& 流失风险（R 标准化）
    g = c.groupby("segment").agg(
        人数=("user_id", "size"),
        群体总销售额=("M_消费金额", "sum"),
        人均消费金额=("M_消费金额", "mean"),
        购买频次=("F_购买频次", "mean"),
        促销响应率=("促销金额占比", "mean"),
        最近购买间隔=("R_最近购买间隔", "mean"),
    )
    # 复购率：群体内购买频次>=2 的人占比
    g["复购率"] = c.groupby("segment").apply(lambda x: (x["F_购买频次"] >= 2).mean())
    g["流失风险"] = g["最近购买间隔"]
    metrics = ["群体总销售额", "人均消费金额", "购买频次", "复购率", "促销响应率", "流失风险"]
    benefit = [True, True, True, True, True, False]   # 流失风险为负向
    X = g[metrics].values
    w, _ = critic_weights(X, benefit)
    score, _ = topsis(X, w, benefit)
    g["营销价值得分"] = score.round(4)
    g["价值排名"] = g["营销价值得分"].rank(ascending=False).astype(int)
    g = g.sort_values("营销价值得分", ascending=False)
    g["销售贡献占比"] = (g["群体总销售额"] / g["群体总销售额"].sum()).round(4)
    return g.reset_index(), dict(zip(metrics, w.round(4)))


# ===========================================================================
# 2. 商品组合促销决策（HUIM + 关联规则 → TOPSIS）
# ===========================================================================
def bundle_strategy(df, hui, rules):
    pos = df[df["is_return"] == 0]
    # 以 HUIM 高效用组合为主，匹配小类级规则的 confidence/lift
    l3rules = rules[rules["层级"] == "小类级"].copy()
    rule_map = {}
    for _, r in l3rules.iterrows():
        key = frozenset(r["前项"].split("+") + [r["后项"]])
        rule_map.setdefault(key, []).append((r["置信度"], r["提升度"]))

    rows = []
    for _, h in hui.iterrows():
        items = h["组合"].split("+")
        key = frozenset(items)
        conf = lift = np.nan
        # 寻找包含该组合的规则
        best = None
        for k, v in rule_map.items():
            if key <= k or k <= key:
                for cf, lf in v:
                    if best is None or lf > best[1]:
                        best = (cf, lf)
        if best:
            conf, lift = best
        # 跨类目：不同大类
        l1s = pos[pos["cat_l3_name"].isin(items)]["cat_l1_name"].nunique()
        # 促销提升：组合内商品促销 vs 非促销篮均金额（粗略）
        sub = pos[pos["cat_l3_name"].isin(items)]
        promo_amt = sub[sub["is_promo"] == 1]["amount"].mean()
        nonpromo_amt = sub[sub["is_promo"] == 0]["amount"].mean()
        if (not nonpromo_amt) or np.isnan(nonpromo_amt) or np.isnan(promo_amt):
            promo_lift = 1.0   # 该组合无促销记录（如生鲜）→ 中性
        else:
            promo_lift = promo_amt / nonpromo_amt
        rows.append({
            "组合": h["组合"], "项数": h["项数"], "支持度": h["支持度"],
            "置信度": round(conf, 3) if not np.isnan(conf) else 0.3,
            "提升度": round(lift, 3) if not np.isnan(lift) else 1.2,
            "总效用": h["总效用"], "篮均效用": h["篮均效用"],
            "促销提升度": round(promo_lift, 3), "跨类目数": l1s,
            "可触达篮数": h["出现篮数"],
        })
    bdf = pd.DataFrame(rows)
    # TOPSIS BundleScore
    metrics = ["支持度", "置信度", "提升度", "总效用", "促销提升度", "可触达篮数"]
    X = bdf[metrics].values
    w, _ = critic_weights(X)
    bdf["组合价值得分"] = topsis(X, w)[0].round(4)
    bdf = bdf.sort_values("组合价值得分", ascending=False).reset_index(drop=True)
    # 策略建议
    def strat(r):
        if r["跨类目数"] >= 2:
            return "跨品类联动·第二件折扣"
        if r["促销提升度"] > 1.1:
            return "满减组合·捆绑促销"
        return "联动陈列·常购组合"
    bdf["策略建议"] = bdf.apply(strat, axis=1)
    return bdf, dict(zip(metrics, w.round(4)))


# ===========================================================================
# 3. 促销响应分析：朴素 PromoLift  vs  DML 因果效应
# ===========================================================================
def promotion_response(df, cust, seg):
    pos = df[df["is_return"] == 0].copy()
    pos = pos.merge(seg[["user_id", "segment"]], on="user_id", how="left")
    pos = pos.merge(cust[["user_id", "M_消费金额", "F_购买频次", "促销敏感度"]], on="user_id", how="left")

    # --- 朴素 PromoLift（群体级，混淆）---
    naive_rows = []
    for s, gd in pos.groupby("segment"):
        ap = gd[gd["is_promo"] == 1]["amount"].mean()
        an = gd[gd["is_promo"] == 0]["amount"].mean()
        naive_rows.append({"群体": s, "促销笔均金额": round(ap, 2), "非促销笔均金额": round(an, 2),
                           "朴素PromoLift": round(ap / an, 3) if an else np.nan,
                           "促销销售占比": round(gd[gd["is_promo"] == 1]["amount"].sum() / gd["amount"].sum(), 4)})
    naive_df = pd.DataFrame(naive_rows)

    # --- DML 去偏因果效应 ---
    # 混淆变量 X：大类(one-hot) + 单价 + 价格分位 + 时间 + 顾客特征
    ip = pos.groupby(["cat_l3_code", "item_id"])["unit_price"].mean().reset_index()
    ip["price_rank"] = ip.groupby("cat_l3_code")["unit_price"].rank(pct=True)
    pos = pos.merge(ip[["item_id", "price_rank"]], on="item_id", how="left")
    pos["price_rank"] = pos["price_rank"].fillna(0.5)
    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    cat_oh = ohe.fit_transform(pos[["cat_l1_name"]])
    Xnum = pos[["unit_price", "price_rank", "weekday", "is_weekend", "sale_month",
                "M_消费金额", "F_购买频次"]].fillna(0).values
    X = np.hstack([Xnum, cat_oh])
    T = pos["is_promo"].values
    Y = pos["amount"].values

    naive_ate = naive_diff(T, Y)
    cate = dml_group_cate(X, T, Y, pos["segment"].fillna("未知").values,
                          n_folds=5, discrete_treatment=True)
    overall = cate.pop("_overall")

    dml_rows = [{"群体": "全体(ATE)", "DML因果效应": round(overall["theta"], 3),
                 "标准误": round(overall["se"], 3),
                 "95%CI下": round(overall["ci95"][0], 3), "95%CI上": round(overall["ci95"][1], 3),
                 "样本数": overall["n"], "朴素均值差": round(naive_ate, 3)}]
    for s, v in cate.items():
        dml_rows.append({"群体": s, "DML因果效应": round(v["theta"], 3),
                         "标准误": round(v["se"], 3),
                         "95%CI下": round(v["ci95"][0], 3), "95%CI上": round(v["ci95"][1], 3),
                         "样本数": v["n"], "朴素均值差": np.nan})
    dml_df = pd.DataFrame(dml_rows)

    resp = naive_df.merge(
        dml_df[dml_df["群体"] != "全体(ATE)"][["群体", "DML因果效应", "95%CI下", "95%CI上"]],
        on="群体", how="left")
    return resp, dml_df, overall, naive_ate


# ===========================================================================
# 4. 品类经营分析
# ===========================================================================
def category_operation(df):
    pos = df[df["is_return"] == 0]
    total = pos["amount"].sum()
    rows = []
    for cat, gd in pos.groupby("cat_l1_name"):
        sales = gd["amount"].sum()
        buyers = gd["user_id"].nunique()
        repeat = (gd.groupby("user_id").size() >= 2).mean()
        promo_dep = gd[gd["is_promo"] == 1]["amount"].sum() / sales
        # 增长：4月 vs 1月
        ms = gd.groupby("sale_month")["amount"].sum()
        g1 = ms.get(202501, np.nan); g4 = ms.get(202504, np.nan)
        growth = (g4 - g1) / g1 if g1 and not np.isnan(g1) and g1 > 0 else np.nan
        rows.append({"大类": cat, "销售贡献": sales / total, "购买人数": buyers,
                     "复购率": round(repeat, 3), "促销依赖度": round(promo_dep, 3),
                     "增长率": round(growth, 3) if not np.isnan(growth) else 0.0,
                     "人均金额": round(sales / buyers, 2)})
    cdf = pd.DataFrame(rows).sort_values("销售贡献", ascending=False)
    med_contrib = cdf["销售贡献"].median()
    med_rep = cdf["复购率"].median()
    med_amt = cdf["人均金额"].median()

    def classify(r):
        if r["促销依赖度"] >= 0.30:
            return "促销依赖类目"
        if r["增长率"] >= 0.10 and r["销售贡献"] < med_contrib:
            return "增长潜力类目"
        if r["销售贡献"] >= med_contrib and r["复购率"] >= med_rep:
            return "核心稳定类目"
        if r["人均金额"] >= med_amt and r["复购率"] < med_rep:
            return "高价值低频类目"
        return "长尾弱势类目"
    cdf["类目类型"] = cdf.apply(classify, axis=1)
    strategy = {"核心稳定类目": "保供应·会员权益", "增长潜力类目": "增曝光·交叉推荐",
                "促销依赖类目": "控促销成本·提毛利", "高价值低频类目": "精准推荐·场景营销",
                "长尾弱势类目": "打包清理·降库存"}
    cdf["经营策略"] = cdf["类目类型"].map(strategy)
    cdf["销售贡献"] = cdf["销售贡献"].round(4)
    return cdf.reset_index(drop=True)


def main():
    set_style()
    df, cust, seg, hui, rules = load_inputs()

    # 1 群体价值
    sv, sv_w = segment_value(df, cust, seg)
    save_csv(sv.round(3), "segment_value_rank.csv")
    print("=== 群体营销价值排名 ===")
    print(sv[["segment", "人数", "销售贡献占比", "营销价值得分", "价值排名"]].to_string(index=False))

    # 2 组合促销
    bdf, b_w = bundle_strategy(df, hui, rules)
    save_csv(bdf.round(3), "bundle_strategy.csv")
    print("\n=== Top5 组合促销策略 ===")
    print(bdf.head(5)[["组合", "组合价值得分", "促销提升度", "策略建议"]].to_string(index=False))

    # 3 促销响应（DML）
    resp, dml_df, overall, naive_ate = promotion_response(df, cust, seg)
    save_csv(resp.round(3), "promotion_response.csv")
    save_csv(dml_df.round(3), "promotion_dml_effect.csv")
    print("\n=== 促销因果效应（DML）===")
    print(f"朴素均值差 = {naive_ate:.3f} 元/笔  vs  DML去偏 ATE = {overall['theta']:.3f} 元/笔 "
          f"(95%CI [{overall['ci95'][0]:.2f},{overall['ci95'][1]:.2f}])")
    print(dml_df[["群体", "DML因果效应", "95%CI下", "95%CI上", "样本数"]].to_string(index=False))

    # 4 品类经营
    cdf = category_operation(df)
    save_csv(cdf, "category_operation_strategy.csv")
    print("\n=== 品类经营策略 ===")
    print(cdf[["大类", "销售贡献", "复购率", "促销依赖度", "增长率", "类目类型", "经营策略"]].to_string(index=False))

    _plots(df, cust, seg, sv, bdf, dml_df, overall, naive_ate, cdf)
    _write_report(sv, bdf, resp, dml_df, overall, naive_ate, cdf, sv_w, b_w)
    return sv, bdf, resp, cdf


def _plots(df, cust, seg, sv, bdf, dml_df, overall, naive_ate, cdf):
    # 图16：不同群体推荐类目分布（各群体大类金额占比堆叠）
    pos = df[df["is_return"] == 0].merge(seg[["user_id", "segment"]], on="user_id", how="left")
    pivot = pos.pivot_table(index="segment", columns="cat_l1_name", values="amount",
                            aggfunc="sum", fill_value=0)
    share = pivot.div(pivot.sum(axis=1), axis=0)
    topcats = share.sum().sort_values(ascending=False).head(6).index
    share = share[topcats]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bottom = np.zeros(len(share))
    for i, c in enumerate(topcats):
        ax.bar(share.index, share[c], bottom=bottom, color=PALETTE[i % len(PALETTE)],
               label=c, edgecolor="white", width=0.7)
        bottom += share[c].values
    ax.set_ylabel("大类销售金额占比"); ax.legend(ncol=6, fontsize=8, loc="upper center",
                                            bbox_to_anchor=(0.5, 1.12))
    ax.tick_params(axis="x", rotation=20)
    for lab in ax.get_xticklabels():
        lab.set_ha("right"); lab.set_fontsize(8)
    savefig(fig, "16_群体推荐类目分布.png")

    # 群体价值雷达
    metrics = ["群体总销售额", "人均消费金额", "购买频次", "复购率", "促销响应率"]
    cen = sv.set_index("segment")[metrics]
    cen_n = (cen - cen.min()) / (cen.max() - cen.min() + 1e-9)
    ang = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist(); ang += ang[:1]
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    for i, (s, row) in enumerate(cen_n.iterrows()):
        v = row.tolist() + row.tolist()[:1]
        ax.plot(ang, v, color=PALETTE[i % len(PALETTE)], lw=1.8, label=s)
        ax.fill(ang, v, color=PALETTE[i % len(PALETTE)], alpha=0.08)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(metrics, fontsize=9); ax.set_yticklabels([])
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)
    savefig(fig, "mk_群体价值雷达.png")

    # 图：DML 促销因果效应（森林图 + 朴素对比）
    d = dml_df.copy()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    y = np.arange(len(d))
    colors = [PALETTE[1] if g == "全体(ATE)" else PALETTE[0] for g in d["群体"]]
    ax.errorbar(d["DML因果效应"], y,
                xerr=[d["DML因果效应"] - d["95%CI下"], d["95%CI上"] - d["DML因果效应"]],
                fmt="o", color="#333", ecolor="#888", capsize=4, markersize=6, lw=1.2)
    for i, c in enumerate(colors):
        ax.plot(d["DML因果效应"].iloc[i], y[i], "o", color=c, markersize=8)
    ax.axvline(0, color="#C82423", ls="--", lw=1.2, label="零效应")
    ax.axvline(naive_ate, color="#54B345", ls=":", lw=1.5, label=f"朴素均值差={naive_ate:.2f}")
    ax.set_yticks(y); ax.set_yticklabels(d["群体"], fontsize=9)
    ax.set_xlabel("促销对笔均销售额的因果效应 (元/笔)")
    ax.legend(fontsize=9)
    savefig(fig, "mk_促销因果效应.png")

    # 品类经营象限（贡献 vs 复购，气泡=促销依赖）
    fig, ax = plt.subplots(figsize=(9, 6))
    sizes = cdf["促销依赖度"] * 800 + 60
    type_color = {t: PALETTE[i] for i, t in enumerate(cdf["类目类型"].unique())}
    for t in cdf["类目类型"].unique():
        sub = cdf[cdf["类目类型"] == t]
        ax.scatter(sub["销售贡献"], sub["复购率"], s=sub["促销依赖度"] * 800 + 60,
                   color=type_color[t], alpha=0.7, edgecolors="#555", label=t)
    for _, r in cdf.iterrows():
        ax.annotate(r["大类"], (r["销售贡献"], r["复购率"]), fontsize=8,
                    xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("销售贡献占比"); ax.set_ylabel("复购率")
    ax.set_xscale("log")
    ax.legend(fontsize=8, title="类目类型", title_fontsize=8)
    savefig(fig, "mk_品类经营象限.png")

    # 组合促销价值 Top10
    top = bdf.head(10)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(top["组合"][::-1], top["组合价值得分"][::-1], color=PALETTE[3], edgecolor="white")
    ax.set_xlabel("组合价值得分 (TOPSIS)")
    savefig(fig, "14b_组合促销价值.png")


def _write_report(sv, bdf, resp, dml_df, overall, naive_ate, cdf, sv_w, b_w):
    top_seg = sv.iloc[0]
    lines = []
    lines.append("# 营销策略报告 (marketer_report.md)\n")
    lines.append("> 自动生成 ｜ 数据：2025-01 ~ 2025-04 超市销售明细\n")
    lines.append("## 一、顾客群体结构与价值\n")
    lines.append(f"共识别 **{len(sv)} 个顾客群体**。营销价值排名第一为 **{top_seg['segment']}**"
                 f"（人数 {int(top_seg['人数'])}，销售贡献 {top_seg['销售贡献占比']*100:.1f}%）。\n")
    lines.append("| 排名 | 群体 | 人数 | 销售贡献 | 价值得分 |\n|---|---|---|---|---|")
    for _, r in sv.iterrows():
        lines.append(f"| {int(r['价值排名'])} | {r['segment']} | {int(r['人数'])} | "
                     f"{r['销售贡献占比']*100:.1f}% | {r['营销价值得分']:.3f} |")
    lines.append(f"\n价值评估 CRITIC 权重：{sv_w}\n")

    lines.append("\n## 二、促销响应：因果视角（DML）\n")
    lines.append(f"朴素均值差显示促销笔均金额变化 **{naive_ate:+.2f} 元**，但其混淆了「被促销商品本身的品类/价格差异」。")
    lines.append(f"双重机器学习(DML)在控制品类、单价、价格分位、时间、顾客特征后，估计促销对笔均销售额的"
                 f"**去偏因果效应 ATE = {overall['theta']:+.2f} 元/笔**（95%CI "
                 f"[{overall['ci95'][0]:.2f}, {overall['ci95'][1]:.2f}]）。\n")
    sig = "显著" if overall["ci95"][0] * overall["ci95"][1] > 0 else "不显著"
    lines.append(f"该效应在统计上**{sig}**。各群体异质效应(CATE)见 `promotion_dml_effect.csv` 与图 `mk_促销因果效应.png`。\n")
    # 找出 CATE 最高群体
    cate_only = dml_df[dml_df["群体"] != "全体(ATE)"].copy()
    if not cate_only.empty:
        best = cate_only.loc[cate_only["DML因果效应"].idxmax()]
        lines.append(f"促销因果响应最强群体：**{best['群体']}**（CATE {best['DML因果效应']:+.2f} 元/笔）→ 优先投放促销资源。\n")

    lines.append("\n## 三、商品组合促销策略\n")
    lines.append("| 组合 | 价值得分 | 促销提升度 | 策略 |\n|---|---|---|---|")
    for _, r in bdf.head(8).iterrows():
        lines.append(f"| {r['组合']} | {r['组合价值得分']:.3f} | {r['促销提升度']:.2f} | {r['策略建议']} |")

    lines.append("\n## 四、品类经营建议\n")
    lines.append("| 大类 | 销售贡献 | 复购率 | 促销依赖 | 类型 | 策略 |\n|---|---|---|---|---|---|")
    for _, r in cdf.iterrows():
        lines.append(f"| {r['大类']} | {r['销售贡献']*100:.1f}% | {r['复购率']:.2f} | "
                     f"{r['促销依赖度']:.2f} | {r['类目类型']} | {r['经营策略']} |")

    lines.append("\n## 五、差异化投放建议\n")
    strat_map = {
        "高价值稳定型": "会员权益、积分加倍、新品首发，避免过度降价",
        "高价值稳定型2": "交叉推荐、维稳关怀、阶梯权益",
        "促销敏感型": "优惠券、满减、限时折扣、低价带组合",
        "促销敏感型2": "低门槛券、限时折扣拉动频次",
        "生鲜高频型": "生鲜周期券、早晚市优惠、补货提醒",
        "流失预警型": "召回券 + 常购商品提醒 + 短信触达",
        "类目集中型": "同类升级与替代、精准类目营销",
        "跨类探索型": "新品试用、跨品类联动促销",
        "低频偶发型": "低门槛新人券、热门刚需推荐",
    }
    for _, r in sv.iterrows():
        s = r["segment"]
        lines.append(f"- **{s}**（价值排名 {int(r['价值排名'])}）：{strat_map.get(s, '常规运营')}")

    import os
    with open(os.path.join(DOCS_DIR, "marketer_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n[REPORT] marketer_report.md 已生成")


if __name__ == "__main__":
    main()
