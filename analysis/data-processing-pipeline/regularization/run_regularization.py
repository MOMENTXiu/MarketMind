# -*- coding: utf-8 -*-
"""MarketMind 数据正则化引擎 · 驱动脚本（可移植）。
用法：
    python run_regularization.py                  # 处理 ./test_data/ 下所有 csv/xlsx
    python run_regularization.py path1 path2 ...   # 处理指定文件
产物落盘到 ./outputs/{数据集}/。仅做正则化，不做数据分析。
"""
import sys
import io
import os
import glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import RegularizationPipeline, save_all, VERSION

import pandas as pd

TEST_DIR = os.path.join(HERE, "test_data")
OUT = os.path.join(HERE, "outputs")


def show(result, name):
    q, cap, mani = result["quality"], result["capability"], result["manifest"]
    print(f"\n{'='*68}\n数据集: {name}  ({mani['format']} / 编码={mani['encoding']} / sheet={mani['sheet_name']})\n{'='*68}")
    print("【字段映射·已采用(≥0.90)】")
    for d in result["mapping_detail"]:
        if d["standard_field"] and d["confidence"] >= 0.90:
            print(f"  {d['raw_column']:22s} -> {d['standard_field']:14s} {d['confidence']:.2f}")
    cand = [d for d in result["mapping_detail"] if d["standard_field"] and d["confidence"] < 0.90]
    if cand:
        print("【候选·未自动采用(<0.90,待人工确认)】")
        for d in cand:
            print(f"  {d['raw_column']:22s} ~> {d['standard_field']:14s} {d['confidence']:.2f}  {d['status']}")
    unmapped = [d["raw_column"] for d in result["mapping_detail"] if not d["standard_field"]]
    if unmapped:
        print("  未映射列:", ", ".join(unmapped))
    print(f"\n【质量】原始 {q['raw_rows']} → 正则化 {q['normalized_rows']} 行 "
          f"(去重 {q['duplicate_rows_removed']}) | 退货 {q['return_rows']}")
    print(f"  可用标准字段({len(q['available_standard_fields'])}): {q['available_standard_fields']}")
    print(f"  数据可分析评分 = {q['analysis_ready_score']}  ({q['grade']})")
    print(f"【业务规则】{mani['rules_applied']}")
    print(f"【分析能力】可运行 {cap['runnable_count']}/9")
    if cap["degraded_fields"]:
        print("  降级:", cap["degraded_fields"])


def main():
    args = sys.argv[1:]
    if args:
        files = args
    else:
        files = sorted(glob.glob(os.path.join(TEST_DIR, "*.csv")) +
                       glob.glob(os.path.join(TEST_DIR, "*.xlsx")) +
                       glob.glob(os.path.join(TEST_DIR, "*.xls")))
    print(f"MarketMind 正则化引擎 {VERSION} | 待处理 {len(files)} 个文件")
    pipe = RegularizationPipeline()
    summary = []
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        result = pipe.run(fp)
        save_all(result, os.path.join(OUT, name))
        show(result, name)
        q, cap = result["quality"], result["capability"]
        summary.append({"数据集": name, "格式": result["manifest"]["format"],
                        "编码": result["manifest"]["encoding"] or "-",
                        "原始行": q["raw_rows"], "正则化行": q["normalized_rows"],
                        "映射字段数": q["mapped_field_count"],
                        "可分析评分": q["analysis_ready_score"], "评级": q["grade"],
                        "可运行能力数": cap["runnable_count"]})
    if summary:
        os.makedirs(OUT, exist_ok=True)
        sm = pd.DataFrame(summary)
        sm.to_csv(os.path.join(OUT, "regularization_summary.csv"),
                  index=False, encoding="utf-8-sig")
        print(f"\n{'='*68}\n汇总:\n{sm.to_string(index=False)}")


if __name__ == "__main__":
    main()
