# -*- coding: utf-8 -*-
"""普适分析引擎 · 编排器
读取正则化标准数据 + capability，自适应运行各分析模块（按能力 + 运行时校验，缺字段降级而非失败）。
对三组数据统一处理，输出每数据集结果 + 跨数据集汇总。
"""
import sys
import io
import json
import traceback
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from config_3 import (DATASETS, load_normalized, load_capability, set_style,
                      save_csv, OUT_ROOT)
import mod_overview, mod_profile_segment, mod_association, mod_recommendation, mod_promotion

# 模块 -> (capability 键, 运行函数)
MODULES = [
    ("基础销售统计/描述", "can_run_sales_stats", mod_overview.run),
    ("顾客画像与分群", "can_run_customer_profile", mod_profile_segment.run),
    ("关联规则", "can_run_association", mod_association.run),
    ("个性化推荐", "can_run_recommendation", mod_recommendation.run),
    ("促销/折扣因果", "can_run_promotion_analysis", mod_promotion.run),
]


def run_dataset(ds):
    print(f"\n{'#'*72}\n# 数据集: {ds}\n{'#'*72}")
    df = load_normalized(ds); cap = load_capability(ds)
    print(f"加载 {df.shape} | 可运行能力 {cap['runnable_count']}/9")
    results = {}
    for label, capkey, fn in MODULES:
        can = cap.get(capkey, True)
        if not can:
            print(f"\n[跳过] {label}：capability={capkey} 为 False（缺字段降级）")
            results[label] = {"status": "skipped_capability"}
            continue
        print(f"\n[运行] {label} ...")
        try:
            res = fn(df, ds, cap)
            results[label] = res
            if isinstance(res, dict) and res.get("status") == "skipped":
                print(f"   → 运行时跳过：{res.get('reason')}")
            else:
                print(f"   → 完成：{_brief(res)}")
        except Exception as e:
            results[label] = {"status": "error", "error": str(e)}
            print(f"   → 错误：{e}")
            traceback.print_exc()
    # 落盘该数据集结果摘要
    with open(f"{OUT_ROOT}/{ds}/result_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    return results


def _brief(res):
    if not isinstance(res, dict):
        return str(res)
    keys = ["n_rules", "top_rule", "n_segments", "silhouette", "best_model",
            "fusion_hit", "naive_diff", "dml_ate", "top_category", "pareto_top20pct_share"]
    return ", ".join(f"{k}={res[k]}" for k in keys if k in res)


def main():
    set_style()
    allres = {}
    for ds in DATASETS:
        allres[ds] = run_dataset(ds)

    # 跨数据集汇总
    rows = []
    for ds, r in allres.items():
        seg = r.get("顾客画像与分群", {})
        asso = r.get("关联规则", {})
        rec = r.get("个性化推荐", {})
        promo = r.get("促销/折扣因果", {})
        ov = r.get("基础销售统计/描述", {})
        rows.append({
            "数据集": ds,
            "分群数": seg.get("n_segments"),
            "分群轮廓系数": seg.get("silhouette"),
            "关联规则状态": asso.get("status"),
            "关联规则数": asso.get("n_rules", "—"),
            "Top关联": asso.get("top_rule", "—"),
            "推荐最佳模型": rec.get("best_model", "—"),
            "推荐融合HitRate@10": rec.get("fusion_hit", "—"),
            "促销朴素差": promo.get("naive_diff", "—"),
            "促销DML_ATE": promo.get("dml_ate", "—"),
            "主力类目": ov.get("top_category", "—"),
        })
    summ = pd.DataFrame(rows)
    import os
    os.makedirs(OUT_ROOT, exist_ok=True)
    summ.to_csv(f"{OUT_ROOT}/cross_dataset_summary.csv", index=False, encoding="utf-8-sig")
    print(f"\n{'='*72}\n跨数据集汇总:\n{'='*72}")
    print(summ.to_string(index=False))
    print(f"\n[汇总] {OUT_ROOT}/cross_dataset_summary.csv")


if __name__ == "__main__":
    main()
