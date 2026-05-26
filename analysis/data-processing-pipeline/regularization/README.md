# MarketMind 数据正则化引擎（Data Regularization Engine）

将**任意来源**的零售数据（不同语言列名 / 编码 / 格式 / 字段口径）自动 **识别 → 映射 → 校验 → 清洗 → 补全** 为 MarketMind 标准数据 Schema，使下游分析对数据接入具有普适性。

> 设计依据：`design_report.md`（数据正则化模块分析与设计思路报告）。本目录为可独立运行的**核心引擎**实现。

## 目录结构
```
regularization/
├── engine/                      正则化引擎包
│   ├── field_aliases.py         标准 Schema + 中英别名词典 + 单位/促销别名
│   ├── file_reader.py           编码自动识别 / Excel 多 Sheet / 表头检测
│   ├── schema_profiler.py       字段画像（类型/缺失/唯一/值模式/样本）
│   ├── schema_mapper.py         字段映射：四维打分 + 置信度分级 + 贪心 1:1
│   ├── type_normalizer.py       日期/数值/促销/ID 规范化 + 时间派生
│   ├── business_normalizer.py   伪订单号/金额数量单价互补/单位归一/退货/促销/类目兜底
│   ├── quality_checker.py       质量指标 + 数据可分析评分
│   ├── capability_checker.py    分析能力判断与降级
│   └── pipeline.py              编排 RegularizationPipeline + 落盘 save_all
├── run_regularization.py        驱动脚本
├── test_data/                   测试数据（order_1 英文/GBK、order_2 中文/UTF-8）
├── outputs/                     正则化产物（dataset.csv + 7 个 json / 数据集）
├── project_plan.md  report.md  design_report.md
```

## 用法
```bash
cd regularization
python run_regularization.py                 # 处理 test_data/ 下全部文件
python run_regularization.py 路径1 路径2 ...   # 处理指定文件
```
产物落盘到 `outputs/{数据集}/`：`dataset.csv`（标准化明细）、`schema_mapping.json`、
`schema_mapping_detail.json`、`field_profile.json`、`quality_report.json`、
`capability.json`、`manifest.json`、`preview_rows.json`。

代码内调用：
```python
from engine import RegularizationPipeline, save_all
res = RegularizationPipeline().run("path/to/任意销售数据.csv")
save_all(res, "outputs/xxx")
```

## 标准 Schema
- core：`user_id` `sale_date` `item_id` `amount`
- recommended：`quantity` `unit_price`
- basket：`order_id` `cat_l1_name` `cat_l2_name` `cat_l3_name` `item_name`
- marketing：`is_promo` `discount` `profit` `item_type` `unit` `spec` `store_id` `region` `city` `segment` `gender` `age` `brand`

## 关键设计
| 机制 | 说明 |
|---|---|
| 字段映射打分 | `0.45·名称 + 0.25·类型 + 0.20·模式 + 0.10·分布`；别名精确命中直给 ≥0.90 |
| 列名证据下限 | 名称分 <0.5 时总分封顶 0.65，杜绝"仅靠类型蹭分"的错配 |
| 自动采用阈值 0.90 | 仅自动采用高置信映射；0.70–0.90 标 `need_review` 待人工确认；<0.70 仅候选 |
| 编码识别 | utf-8-sig→utf-8→gbk→gb18030→big5→latin1，兜底 charset-normalizer |
| 业务降级 | 无订单号→伪订单号；无单价→金额/数量推导；无促销→由折扣推导；缺类目→逐级兜底 |
| 能力判断 | 输出 `capability.json`，下游按可运行能力选择执行，缺字段降级而非失败 |

## 测试结果（普适性验证）
| 数据集 | 列名/编码 | 行数 | 映射字段 | 可分析评分 | 可运行能力 |
|---|---|---|---|---|---|
| order_1 | 英文 / GBK / 电商 | 1693 | 14 精确命中 | 93.8 优秀 | 8/9（无利润→降级）|
| order_2 | 中文 / UTF-8 / Superstore | 9959 | 14 精确命中 | 97.9 优秀 | 9/9 |

两套语言、编码、字段口径完全不同的数据均被正确归一到同一标准 Schema。对原项目 `销售数据.csv`（中文/GBK/三级类目）运行时，引擎自动复现了其手工预处理的关键决策（去重 3 行、退货 93 行、伪订单号=顾客+日期、促销率 15.19%、单位归一）。详见 `report.md`。
