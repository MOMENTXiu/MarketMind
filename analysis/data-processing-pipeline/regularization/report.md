# 实验报告 · 数据正则化引擎测试

> 脚本：`code_files_2/regularization/*` + `run_regularization.py`
> 测试数据：`data/test_data/order_1.csv`、`order_2.csv`（仅正则化，不做分析）

## 1. 测试数据（刻意构造高差异，检验普适性）
| 数据集 | 列名语言 | 编码 | 行数 | 业务类型 | 字段特点 |
|---|---|---|---|---|---|
| order_1 | **英文** | **GBK** + CRLF | 1693 | 电商订单 | 有 order_id/product_id/price/promotion_type/gender/age |
| order_2 | **中文** | **UTF-8 BOM** | 9959 | Superstore 零售 | 有 折扣/利润/细分/地区，**无单价、无促销列** |

## 2. 处理流程
`FileReader（编码/表头）→ SchemaProfiler（字段画像）→ SchemaMapper（四维打分+置信度）→ TypeNormalizer（类型+时间派生）→ BusinessNormalizer（业务补全）→ QualityChecker → CapabilityChecker → 落盘`

## 3. 结果

### 3.1 汇总
| 数据集 | 格式 | 编码(自动识别) | 原始行 | 正则化行 | 映射字段数 | 可分析评分 | 评级 | 可运行能力 |
|---|---|---|---|---|---|---|---|---|
| order_1 | csv | gbk | 1693 | 1693 | 14 | **93.8** | 优秀 | 8/9 |
| order_2 | csv | utf-8-sig | 9959 | 9959 | 14 | **97.9** | 优秀 | 9/9 |

### 3.2 字段映射（均为精确命中，置信度 1.00）
- **order_1（英文→标准）**：order_id→order_id、user_id→user_id、product_id→**item_id**、order_time→**sale_date**、quantity→quantity、amount→amount、price→**unit_price**、promotion_type→**is_promo**、category→**cat_l1_name**、product_name→**item_name**、shipping_city→city、gender/age/brand。
- **order_2（中文→标准）**：订单ID→order_id、订单日期→sale_date、客户ID→**user_id**、产品ID→**item_id**、销售额→**amount**、数量→quantity、折扣→discount、利润→profit、类别→cat_l1_name、子类别→**cat_l3_name**、产品名称→item_name、细分→segment、城市→city、地区→region。

低置信候选（如 order_1 的 `is_hot→discount` 0.83、`launch_date→cat_l3_name` 0.56）被正确**标记 need_review/weak 但不自动采用**，避免错配。

### 3.3 类型与业务正则化验证
| 验证点 | order_1 | order_2 |
|---|---|---|
| 编码自动识别 | gbk ✔ | utf-8-sig ✔ |
| 日期解析率 | 100%（`2024/1/1 8:41`）| 100%（`2024/4/27`）|
| 时间派生 | sale_year/month/day/weekday/is_weekend/week/quarter ✔ | 同 ✔ |
| 促销二值化 | None→0、Coupon/FlashSale/FullDiscount→1（促销率 31.3%）✔ | — |
| 促销兜底 | — | 无 is_promo，**由折扣推导**（discount>0→1）✔ |
| 单价 | 原生 price ✔ | **金额/数量推导**（129.696/2=64.85）✔ |
| 订单号 | 原生 order_id | 原生订单ID（若缺则生成伪订单号）|
| 退货标记 | is_return 计算 ✔ | ✔ |
| 类目兜底 | 缺小类→用大类填充 cat_l3 ✔ | 子类别直接映射 ✔ |
| 溯源 | manifest 记录 encoding/rules/type_stats | order_id/unit_price/is_promo _source 列 |

### 3.4 分析能力判断
- order_1：8/9 可运行，仅**利润分析不可运行**（无 profit，正确降级）。
- order_2：**9/9 全部可运行**（含利润分析）。

## 4. 自评估
| 验收点 | 结论 |
|---|---|
| 格式/编码普适 | ✅ GBK 与 UTF-8 自动识别 |
| 字段语义普适 | ✅ 中英列名均正确映射到同一标准 Schema |
| 类型转换普适 | ✅ 日期/数值/促销/ID 规范化无误 |
| 业务口径普适 | ✅ 缺单价/促销/订单号均自动补全或降级 |
| 错配防护 | ✅ 列名证据下限 + 0.90 阈值，低置信仅候选不采用 |
| 能力可解释 | ✅ capability.json 明确哪些能跑/降级原因 |
| 结果可追溯 | ✅ raw→normalized + mapping/quality/capability/manifest 全产物 |

**结论**：两套语言、编码、字段口径完全不同的零售数据，均被正确归一到统一标准 Schema、评分优秀（93.8 / 97.9），证明正则化引擎对数据接入具有**普适性**，达到可接受的优秀表现，通过检验。

## 5. 产出
- 代码：`code_files_2/regularization/`（9 模块）+ `run_regularization.py`
- 每数据集产物：`output_2/regularized/{name}/`（dataset.csv + 7 个 json）
- 汇总：`output_2/regularized/regularization_summary.csv`
