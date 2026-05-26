# MarketMind 数据正则化引擎 · 实施方案（project_plan_2.md）

> 参照 `docs/MarketMind 数据正则化模块分析与设计思路报告.md`，落地为**可独立运行的核心正则化引擎**。
> 设计原则：方法可按实际调整，以"正则化结果正确、普适"为准（非照搬报告的 FastAPI 全栈结构）。

## 0. 目标
将任意来源零售数据（不同语言列名 / 编码 / 格式 / 字段口径）自动**识别→映射→校验→清洗→补全**为 MarketMind 标准 Schema，使下游分析对数据接入具有普适性。本阶段**仅做正则化，不做数据分析**。

## 1. 代码架构（`code_files_2/`）
```
code_files_2/
├── regularization/                 正则化引擎包
│   ├── field_aliases.py            标准Schema + 中英别名词典 + 单位/促销别名
│   ├── file_reader.py              编码自动识别 / Excel多Sheet / 表头检测
│   ├── schema_profiler.py          字段画像（类型/缺失/唯一/模式/样本）
│   ├── schema_mapper.py            字段映射：四维打分 + 置信度分级 + 贪心1:1
│   ├── type_normalizer.py          日期/数值/促销/ID 类型规范化 + 时间派生
│   ├── business_normalizer.py      伪订单号/金额数量单价互补/单位归一/退货/促销/类目兜底
│   ├── quality_checker.py          质量指标 + 数据可分析评分
│   ├── capability_checker.py       分析能力判断与降级
│   └── pipeline.py                 编排 + 落盘(save_all)
├── run_regularization.py           驱动：跑 test_data 两套数据并验证
├── project_plan_2.md               本文件
└── report_regularization.md        测试实验报告
```
产物落盘：`output_2/regularized/{数据集}/{dataset.csv, schema_mapping.json, schema_mapping_detail.json, field_profile.json, quality_report.json, capability.json, manifest.json, preview_rows.json}`。

## 2. 标准 Schema（核心）
core：user_id / sale_date / item_id / amount；recommended：quantity / unit_price；
basket：order_id / cat_l1_name / cat_l2_name / cat_l3_name / item_name；
marketing：is_promo / discount / profit / item_type / unit / spec / store_id / region / city / segment / gender / age / brand。

## 3. 关键设计决策（结合实际调整）
| 决策 | 说明 |
|---|---|
| 字段映射打分 | `0.45·名称 + 0.25·类型 + 0.20·模式 + 0.10·分布`，别名精确命中直给≥0.90 |
| **列名证据下限** | 名称分<0.5 时总分封顶 0.65，杜绝"仅靠类型蹭分"的错配（如 is_hot→discount）|
| **自动采用阈值 0.90** | 仅自动采用高置信映射；0.70-0.90 标记 need_review 待人工确认；<0.70 仅候选（设计 §15.4）|
| 编码识别 | utf-8-sig→utf-8→gbk→gb18030→big5→latin1，兜底 charset-normalizer |
| 业务降级 | 无订单号→伪订单号；无单价→金额/数量推导；无促销→由折扣推导；缺类目→逐级兜底 |
| 能力判断 | 输出 capability.json，下游按可运行能力选择执行，缺字段降级而非失败 |

## 4. 测试与验收
用 `data/test_data/order_1.csv`（英文列名·GBK·电商）与 `order_2.csv`（中文列名·UTF-8·Superstore）验证普适性。
验收标准：核心字段映射正确、编码自动识别、类型/业务规范化无误、能力判断合理、可分析评分≥85。结果见 `report_regularization.md`。

## 5. 后续可扩展（暂不实现）
模板记忆、正则化版本管理、数据漂移检测、隐私脱敏、产品化（Provider/Pipeline/API）、下游分析能力迁移到标准字段。
