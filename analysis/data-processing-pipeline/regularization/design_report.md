# MarketMind 数据正则化模块分析与设计思路报告

## 基于 `add-analysis-2` 分支的数据普适性能力建设方案

## 1. 报告定位

本报告面向 MarketMind 新版本 `add-analysis-2` 分支，目标是在现有项目分析体系中补充一个**数据正则化模块**，使系统从“能上传数据并运行固定模板分析”，升级为“能适配多来源、多字段、多格式零售数据的通用型营销分析系统”。

这里的“正则化模块”不是机器学习中的 L1/L2 正则化，而是指：

> **Data Regularization / Schema Regularization / 数据正则化**
> 即将用户上传的任意销售明细数据，自动识别、映射、校验、清洗、补全并转换为 MarketMind 标准分析数据结构。

该模块应成为：

```text
数据上传模块
    ↓
数据正则化模块
    ↓
分析建模模块
    ↓
推荐与营销报告模块
```

之间的关键中间层。

------

# 2. 当前 `add-analysis-2` 分支现状分析

## 2.1 当前分支已经具备较好的工程骨架

`add-analysis-2` 分支已经不是简单脚本项目，而是具有较明确的分层结构。后端通过 `ProvidersContainer` 统一组织项目仓储、文件存储、数据集读取、规则存储、推荐模型存储、语音、LLM、分析任务和遥测等 Provider。

FastAPI 层也已经通过依赖注入把控制器和业务管线连接起来，例如项目管线、数据上传管线、客户读取管线、推荐管线、关联分析管线、语音管线和项目分析流等。

Provider 工厂中已经集中创建 `JsonProjectRepositoryAdapter`、`LocalProjectFileStorageAdapter`、`CsvDatasetAdapter`、`LocalGeneratedAssetAdapter`、`LocalRecommendationModelStoreAdapter` 等本地适配器。

这说明正则化模块不应该写成孤立脚本，而应该遵循当前分支的架构方式：

```text
Protocol / Provider
    ↓
Infrastructure Adapter
    ↓
Business Pipeline
    ↓
API Dependency
    ↓
API Route
```

------

## 2.2 当前上传流程已经存在，但只完成了“文件进入系统”

当前 `DatasetUploadPipeline` 负责验证上传文件名、保存数据集、更新项目状态，并提交分析任务。它支持 `.csv`、`.xlsx`、`.xls` 后缀校验。

当前本地文件存储适配器会将上传文件内容保存到：

```text
data/projects/{project_id}/dataset.csv
```

也就是说，无论用户上传的原始文件是什么名字，系统最终主要以 `dataset.csv` 的形式存储项目数据。

这带来一个问题：

> 上传模块只是“存文件”，并没有判断这个文件是否真的符合 MarketMind 后续分析所需的数据标准。

因此，目前系统仍然可能出现：

```text
上传成功
    ↓
分析启动
    ↓
字段不匹配
    ↓
分析失败
```

而正则化模块要解决的就是这中间缺失的“数据标准化与可分析性确认”环节。

------

## 2.3 当前数据读取能力仍偏向固定 CSV

当前 `CsvDatasetAdapter` 的 `load_dataset()` 直接使用：

```python
pd.read_csv(path, encoding="utf-8")
```

读取数据。

它的优点是简单稳定，但不足也很明显：

1. 对 GBK / GB18030 编码文件不友好；
2. 对 Excel 文件没有真正解析逻辑；
3. 对多 Sheet 表格没有选择机制；
4. 对字段别名没有识别能力；
5. 对错误分隔符、BOM、空表头、重复列没有处理；
6. 对上传后的原始文件与清洗后文件没有区分。

因此，正则化模块不能只改分析算法，还必须补强“文件读取层”。

------

## 2.4 当前分析流依赖原始数据直接进入模型

当前 `ProjectAnalysisFlow` 在执行分析时，会先解析项目数据集，然后依次执行关联规则、销售预测、顾客聚类、报告生成、语音生成和推荐模型构建。

当前流程大致是：

```text
load_project_dataset(project_id)
    ↓
analyze_association_rules
    ↓
forecast_sales
    ↓
cluster_customers
    ↓
generate_analysis_report
    ↓
build_recommendation_model
```

这说明只要数据集字段不符合各个能力函数的预期，后续能力就会失败。正则化模块应该把这个流程改成：

```text
load_raw_project_dataset(project_id)
    ↓
regularize_dataset(project_id)
    ↓
load_normalized_project_dataset(project_id)
    ↓
根据 capability.json 有选择地运行分析能力
```

------

## 2.5 当前分析能力对固定字段依赖强

例如，当前关联规则能力直接假设存在：

```text
订单 ID
子类别
```

并使用 `dataset.groupby("订单 ID")["子类别"]` 构建购物篮。

当前顾客聚类能力则依赖：

```text
订单日期
客户 ID
订单 ID
销售额
利润
数量
折扣
细分
地区
```

并直接计算 RFM、利润率、平均折扣、客单价等特征。

当前推荐模型构建能力也继续使用固定中文字段，并且内部以 RFM、KMeans 聚类、类别、子类别、地区、细分等数据结构组织推荐模型。

这意味着：只要用户上传的数据列名不是这些固定列名，即使业务含义完全相同，系统也可能无法分析。

------

## 2.6 当前离线分析脚本已有正则化原型，但没有产品化

`analysis/code_files/data_preprocessing.py` 已经包含一套针对当前销售数据的字段映射、单位归一、错位行修复、去重、日期订正、促销二值化、退货标记、单价填补和数量回填逻辑。

`analysis/code_files/config.py` 中也已经有统一路径、中文绘图、CSV 保存、pkl 保存、MinMax 标准化、CRITIC 权重、TOPSIS、熵权法等通用工具。

这些内容说明 `add-analysis-2` 分支已经具备“离线正则化经验”，但它仍有几个产品化问题：

| 当前离线脚本特点                               | 产品化后应改造为                                |
| ---------------------------------------------- | ----------------------------------------------- |
| 固定读取 `D:\new_Marketmind\data\销售数据.csv` | 读取任意项目上传文件                            |
| 固定字段映射 `RAW2INNER`                       | 可扩展字段别名词典 + 自动识别                   |
| 固定 GBK 编码                                  | 自动编码检测                                    |
| 输出到固定 output 目录                         | 输出到 `data/projects/{project_id}/normalized/` |
| 面向单一数据集                                 | 面向所有上传数据                                |
| 脚本式运行                                     | Pipeline + Provider + API 化运行                |
| 结果主要给离线实验使用                         | 结果供分析流、前端和报告共同使用                |

因此，正则化模块不是从零开始，而是把现有离线清洗经验抽象成一个通用产品能力。

------

# 3. 数据正则化模块建设目标

正则化模块的目标不是“让某个数据集能跑”，而是让 MarketMind 具备“多数据集适配能力”。

核心建设目标如下：

| 目标           | 说明                                             |
| -------------- | ------------------------------------------------ |
| 数据格式普适   | CSV / Excel 均可读取，自动处理编码与 Sheet       |
| 字段语义普适   | 不同列名可以映射为同一标准字段                   |
| 类型转换普适   | 日期、金额、数量、单价、促销字段自动规范化       |
| 业务口径普适   | 无订单号、无利润、无折扣时可降级分析             |
| 分析能力可解释 | 告诉用户哪些分析能跑，哪些不能跑，为什么         |
| 结果可追溯     | 保留 raw、normalized、mapping、quality、manifest |
| 工程可维护     | 后续分析模块只依赖标准字段，不到处写兼容逻辑     |
| 前端可确认     | 低置信度字段映射可以让用户手动确认               |

------

# 4. 正则化模块整体架构

## 4.1 新增模块在当前架构中的位置

基于当前 `add-analysis-2` 分支，建议将正则化模块插入到 `DatasetUploadPipeline` 和 `ProjectAnalysisFlow` 之间。

```text
Project API
    ↓
DatasetUploadPipeline
    ↓
LocalProjectFileStorageAdapter 保存 raw dataset
    ↓
RegularizationPipeline
    ↓
NormalizedDatasetAdapter 保存 normalized dataset
    ↓
ProjectAnalysisFlow 读取 normalized dataset
    ↓
Association / Clustering / Recommendation / Forecast / Report
```

也就是说，上传数据之后，不应该直接进入分析，而应先经过：

```text
文件读取
    ↓
字段识别
    ↓
字段映射
    ↓
类型转换
    ↓
业务补全
    ↓
质量检查
    ↓
能力判断
    ↓
标准数据保存
```

------

## 4.2 目录结构设计

建议在当前 `backend/` 下新增：

```text
backend/
├── regularization/
│   ├── __init__.py
│   ├── schemas.py
│   ├── field_aliases.py
│   ├── file_reader.py
│   ├── schema_profiler.py
│   ├── schema_mapper.py
│   ├── type_normalizer.py
│   ├── business_normalizer.py
│   ├── quality_checker.py
│   ├── capability_checker.py
│   ├── regularization_pipeline.py
│   └── rules/
│       ├── field_aliases.yaml
│       ├── unit_aliases.yaml
│       ├── promo_aliases.yaml
│       ├── date_formats.yaml
│       └── schema_profiles.yaml
```

新增 Provider：

```text
backend/providers/
├── regularization_provider.py
├── regularization_store_provider.py
```

新增 Adapter：

```text
backend/infrastructure/adapters/
├── local_regularization_store_adapter.py
├── pandas_file_reader_adapter.py
```

新增 Pipeline：

```text
backend/business/pipelines/
├── dataset_regularization_pipeline.py
```

新增 API：

```text
backend/api/
├── regularization.py
```

------

# 5. 核心数据产物设计

每个项目的数据目录建议改为：

```text
data/projects/{project_id}/
├── raw/
│   ├── uploaded_original.csv 或 uploaded_original.xlsx
│   └── raw_metadata.json
├── normalized/
│   ├── dataset.csv
│   ├── schema_mapping.json
│   ├── field_profile.json
│   ├── quality_report.json
│   ├── capability.json
│   ├── manifest.json
│   └── preview_rows.json
├── customers.csv
├── report_{project_id}.md
└── report_{project_id}.mp3
```

## 5.1 raw 数据

保存用户原始上传文件，不做覆盖，便于追溯和重新正则化。

## 5.2 normalized 数据

保存分析模块真正使用的数据：

```text
data/projects/{project_id}/normalized/dataset.csv
```

后续所有分析能力只读这个文件，而不直接读 raw 文件。

## 5.3 schema_mapping.json

记录原始字段到标准字段的映射：

```json
{
  "顾客编号": "user_id",
  "销售日期": "sale_date",
  "商品编码": "item_id",
  "销售金额": "amount",
  "是否促销": "is_promo"
}
```

## 5.4 quality_report.json

记录数据质量：

```json
{
  "raw_rows": 42816,
  "normalized_rows": 42814,
  "duplicate_rows_removed": 2,
  "missing_user_id_rate": 0.0,
  "missing_item_id_rate": 0.0,
  "invalid_amount_count": 0,
  "generated_order_id_count": 26120,
  "analysis_ready_score": 91.6
}
```

## 5.5 capability.json

记录该数据能支持哪些分析：

```json
{
  "can_run_association": true,
  "can_run_customer_profile": true,
  "can_run_recommendation": true,
  "can_run_forecast": true,
  "can_run_profit_analysis": false,
  "can_run_promotion_analysis": true,
  "degraded_fields": {
    "order_id": "generated_from_user_date",
    "profit": "missing",
    "discount": "missing"
  }
}
```

## 5.6 manifest.json

记录正则化版本与处理轨迹：

```json
{
  "regularization_version": "v1.0.0",
  "project_id": "xxx",
  "raw_filename": "销售数据.csv",
  "encoding": "gbk",
  "sheet_name": null,
  "created_at": "2026-xx-xxTxx:xx:xx",
  "rules_applied": [
    "field_alias_mapping",
    "date_normalization",
    "promo_binary_mapping",
    "unit_normalization",
    "pseudo_order_id_generation"
  ]
}
```

------

# 6. 标准 Schema 设计

## 6.1 核心必需字段

这些字段决定系统是否具备基础分析能力。

| 标准字段     | 含义     | 必需程度 | 缺失影响                       |
| ------------ | -------- | -------- | ------------------------------ |
| `user_id`    | 顾客编号 | 强必需   | 无法做顾客画像和个性化推荐     |
| `sale_date`  | 销售日期 | 强必需   | 无法做 RFM、时间趋势、复购周期 |
| `item_id`    | 商品编码 | 强必需   | 无法做商品级推荐               |
| `amount`     | 销售金额 | 强必需   | 无法做消费金额、价值贡献       |
| `quantity`   | 销售数量 | 推荐必需 | 可由金额和单价估算             |
| `unit_price` | 商品单价 | 推荐必需 | 可由金额和数量估算             |

## 6.2 购物篮推荐字段

| 标准字段      | 含义            | 缺失处理                     |
| ------------- | --------------- | ---------------------------- |
| `order_id`    | 订单号 / 小票号 | 缺失时生成 `pseudo_order_id` |
| `cat_l1_name` | 大类名称        | 缺失时只做商品级分析         |
| `cat_l2_name` | 中类名称        | 缺失时用大类或小类替代       |
| `cat_l3_name` | 小类名称        | 缺失时用商品编码替代         |
| `item_name`   | 商品名称        | 缺失时用商品编码展示         |

## 6.3 营销分析字段

| 标准字段    | 含义     | 用途                 |
| ----------- | -------- | -------------------- |
| `is_promo`  | 是否促销 | 促销敏感度、促销响应 |
| `discount`  | 折扣     | 折扣敏感度           |
| `profit`    | 利润     | 盈利贡献             |
| `item_type` | 商品类型 | 生鲜 / 一般商品对比  |
| `unit`      | 单位     | 数量口径校验         |
| `spec`      | 规格型号 | 商品展示             |
| `store_id`  | 门店编号 | 多门店分析           |
| `region`    | 地区     | 区域营销             |

------

# 7. 字段识别与映射设计

## 7.1 字段别名词典

以当前新销售数据和旧版示例数据为基础，建立可扩展字段别名库：

```python
FIELD_ALIASES = {
    "user_id": ["顾客编号", "客户ID", "客户 ID", "会员号", "用户编号", "customer_id", "user_id"],
    "order_id": ["订单ID", "订单 ID", "订单编号", "小票号", "流水号", "交易号", "order_id", "bill_no"],
    "sale_date": ["销售日期", "订单日期", "交易日期", "购买日期", "date", "sale_date"],
    "sale_month": ["销售月份", "月份", "年月", "sale_month"],
    "item_id": ["商品编码", "产品ID", "产品 ID", "商品ID", "sku", "sku_id", "item_id"],
    "cat_l1_name": ["大类名称", "一级类目", "商品大类", "category_l1"],
    "cat_l2_name": ["中类名称", "二级类目", "商品中类", "category_l2"],
    "cat_l3_name": ["小类名称", "子类别", "商品小类", "三级类目", "sub_category"],
    "amount": ["销售金额", "销售额", "金额", "实收金额", "成交金额", "amount", "sales"],
    "quantity": ["销售数量", "数量", "销量", "件数", "qty", "quantity"],
    "unit_price": ["商品单价", "单价", "售价", "price", "unit_price"],
    "is_promo": ["是否促销", "促销", "促销标记", "活动标记", "is_promo"]
}
```

## 7.2 映射评分机制

字段映射不能只靠列名完全匹配，应综合列名、数据类型和值分布。

对原始字段 (f) 和标准字段 (s)，定义：
$$
Score(f,s)=
0.45S_{name}
+0.25S_{type}
+0.20S_{pattern}
+0.10S_{distribution}
$$
其中：

| 分数               | 含义           |
| ------------------ | -------------- |
| (S_{name})         | 字段名相似度   |
| (S_{type})         | 数据类型匹配度 |
| (S_{pattern})      | 值模式匹配度   |
| (S_{distribution}) | 分布特征匹配度 |

例如：

- 8 位数字且可解析为日期 → `sale_date`；
- 只包含“是/否、Y/N、0/1” → `is_promo`；
- 唯一值多且重复出现 → 可能是 `user_id` 或 `item_id`；
- 小数多且为正 → 可能是 `amount`、`quantity`、`unit_price`；
- 类别数量少且为中文 → 可能是类目字段。

## 7.3 映射置信度等级

| 置信度    | 状态           | 处理方式             |
| --------- | -------------- | -------------------- |
| ≥ 0.90    | auto_confirmed | 自动确认             |
| 0.70—0.90 | need_review    | 前端提示用户确认     |
| 0.50—0.70 | weak_candidate | 作为候选，不自动采用 |
| < 0.50    | missing        | 认为缺失             |

------

# 8. 文件读取正则化设计

当前分支虽然支持 `.csv`、`.xlsx`、`.xls` 后缀校验，但数据读取层还需要真正支持这些格式。

## 8.1 CSV 编码识别

建议读取顺序：

```text
utf-8-sig
utf-8
gbk
gb18030
```

如果仍失败，再使用 `charset-normalizer` 或 `chardet` 推断。

## 8.2 Excel 读取

Excel 文件处理策略：

1. 读取所有 Sheet 名；
2. 过滤空 Sheet；
3. 默认选第一个有效 Sheet；
4. 如果多个 Sheet 都有效，则前端让用户选择；
5. 支持跳过说明行，自动寻找表头行。

## 8.3 表头识别

可能存在：

```text
第 1 行是说明
第 2 行是空行
第 3 行才是字段名
```

因此需要自动检测表头行：

- 非空值比例高；
- 字符串值比例高；
- 与字段别名词典匹配度高；
- 下一行开始出现数值与日期。

------

# 9. 类型正则化设计

## 9.1 日期正则化

支持：

```text
20250101
2025-01-01
2025/01/01
2025.01.01
2025年1月1日
202501
```

若只有月份字段，例如 `202501`，则转为：

```text
2025-01-01
```

同时派生：

```text
sale_year
sale_month
sale_day
weekday
is_weekend
week_of_year
quarter
```

当前离线清洗脚本已经处理了非法日期，例如非闰年 2 月 29 日订正为当月最后一天，这个逻辑可以保留并模块化。

## 9.2 数值正则化

金额、数量、单价字段需要统一处理：

```text
去除 ￥、元、逗号、空格
识别括号负数
识别百分号
转 float
保留小数
```

例如：

```text
￥1,234.50 → 1234.50
(25.6) → -25.6
```

销售数量不应强制转整数，因为生鲜、水果、肉类等按重量销售时天然是小数。

## 9.3 促销字段正则化

统一为：

```text
1 = 促销
0 = 非促销
```

映射规则：

| 原值                            | 标准值                   |
| ------------------------------- | ------------------------ |
| 是、Y、Yes、促销、活动、true、1 | 1                        |
| 否、N、No、非促销、false、0     | 0                        |
| 空值                            | 0 或 unknown，按配置决定 |

当前离线脚本已经将“是/否”映射为 1/0。

------

# 10. 业务正则化设计

## 10.1 订单号补全

如果有真实订单号：

```text
order_id = 原订单号
```

如果没有订单号，则构造伪订单号：
$$
pseudo_{order_{id}} = user_{id} + sale_{date}
$$
如果存在门店字段：
$$
pseudo_{order_{id}} = store_{id} + user_{id} + sale_date
$$
manifest 中必须记录：

```json
{
  "order_id_source": "generated_from_user_date"
}
```

后续关联规则分析可以使用：

```python
basket_key = "order_id" if order_id_exists else "pseudo_order_id"
```

------

## 10.2 金额、数量、单价互补

三者满足：
$$
amount \approx quantity \times unit_price
$$
补全规则：

| 缺失字段          | 补全方式                                 |
| ----------------- | ---------------------------------------- |
| `amount` 缺失     | `quantity * unit_price`                  |
| `quantity` 缺失   | `amount / unit_price`                    |
| `unit_price` 缺失 | `amount / quantity`                      |
| `unit_price` 异常 | 同商品中位数 → 同小类中位数 → 全局中位数 |

当前离线脚本中已经有单价异常填补、数量缺失回填的实现思路，建议抽象为 `BusinessNormalizer`。

------

## 10.3 单位归一

建议把现有脚本中的单位归一逻辑做成配置文件。

示例：

```yaml
千克:
  - 千克
  - KG
  - kg
  - Kg
  - 公斤
  - 散称
袋:
  - 袋
  - d袋
盒:
  - 盒
  - 合
未知单位:
  - ""
  - "0"
  - "2"
  - "一般"
  - "装"
```

输出：

```text
unit_mapping_report.csv
```

------

## 10.4 退货与异常销售标记

对于：

```text
quantity <= 0
amount <= 0
```

不应简单删除，而应标记：

```text
is_return = 1
```

分析时：

- 销售额统计可根据配置排除退货；
- 用户画像可保留退货行为作为风险特征；
- 推荐模型应默认只使用正向购买记录。

------

## 10.5 类目层级补全

如果缺失某一级类目：

| 缺失情况           | 补全策略                 |
| ------------------ | ------------------------ |
| 缺大类，有中类     | 用中类前缀或“未知大类”   |
| 缺小类，有商品编码 | 使用商品编码作为最低层级 |
| 缺小类，有商品名称 | 用商品名称近似小类       |
| 缺所有类目         | 只做商品级分析           |

------

# 11. 数据质量评估设计

## 11.1 质量报告指标

| 指标           | 说明                    |
| -------------- | ----------------------- |
| 原始行数       | 上传文件原始记录数      |
| 正则化后行数   | 清洗后可用记录数        |
| 完全重复行数   | drop duplicates 数量    |
| 用户 ID 缺失率 | `user_id` 缺失比例      |
| 商品 ID 缺失率 | `item_id` 缺失比例      |
| 日期缺失率     | `sale_date` 缺失比例    |
| 金额异常数     | 金额为空、非数值、≤0    |
| 数量异常数     | 数量为空、非数值        |
| 单价异常数     | 单价为空、非数值、≤0    |
| 促销解析成功率 | `is_promo` 映射成功比例 |
| 生成订单号数量 | pseudo_order_id 数量    |
| 字段覆盖率     | 标准字段映射覆盖情况    |
| 数据可分析评分 | 综合质量评分            |

------

## 11.2 数据可分析评分

定义字段覆盖评分：
$$
S_{field}=
\frac{
\sum_j w_j I(field_j\ available)
}{
\sum_j w_j
}
$$
定义合法性评分：
$$
S_{valid}=
1-
\frac{
invalid_date+invalid_amount+invalid_id
}{
total_rows
}
$$
定义完整性评分：
$$
S_{complete}=1-missing_rate_{weighted}
$$
综合评分：
$$
S_{ready}

0.4S_{field}
+
0.3S_{valid}
+
0.2S_{complete}
+
0.1S_{volume}
$$
评分解释：

| 分数  | 状态 | 系统建议               |
| ----- | ---- | ---------------------- |
| ≥ 85  | 优秀 | 可完整运行分析         |
| 70—85 | 良好 | 可运行大部分分析       |
| 50—70 | 一般 | 建议用户确认字段映射   |
| < 50  | 较差 | 建议重新上传或补充字段 |

------

# 12. 分析能力判断与降级机制

正则化模块必须输出 `capability.json`，让分析流有选择地执行。

## 12.1 能力判断表

| 能力         | 必需字段                         | 降级方案                           |
| ------------ | -------------------------------- | ---------------------------------- |
| 基础销售统计 | `amount`                         | 若无金额，用 `quantity` 做销量统计 |
| 时间趋势     | `sale_date`, `amount`            | 若只有月份，做月度趋势             |
| 顾客画像     | `user_id`, `sale_date`, `amount` | 若无日期，只做消费金额画像         |
| 关联规则     | `basket_key`, `item_key`         | 无订单号时用 pseudo_order_id       |
| 个性化推荐   | `user_id`, `item_id`, `amount`   | 若无用户，只做热门商品推荐         |
| 促销分析     | `is_promo`, `amount`             | 若无促销字段，跳过促销模块         |
| 利润分析     | `profit`                         | 若无利润，用销售金额替代价值       |
| 价格敏感度   | `unit_price`, `amount`           | 若无单价，跳过价格带分析           |

------

## 12.2 分析流改造

当前 `ProjectAnalysisFlow` 是直接按固定顺序运行各分析能力。

建议改为：

```python
dataset = providers.dataset.load_normalized_project_dataset(project_id)
capability = providers.regularization_store.load_capability(project_id)

if capability.can_run_association:
    run_association(dataset)

if capability.can_run_forecast:
    run_forecast(dataset)

if capability.can_run_clustering:
    run_clustering(dataset)

if capability.can_run_recommendation:
    build_recommendation(dataset)
```

这样即使某些字段缺失，也不会导致整个项目失败。

------

# 13. 与当前 Provider 架构的集成方案

## 13.1 扩展 ProvidersContainer

当前 `ProvidersContainer` 已经集中管理 repository、storage、assets、dataset、association_rules、recommendation_models、speech、llm、analysis_jobs、telemetry 等 Provider。

建议新增：

```python
regularization: RegularizationProvider
regularization_store: RegularizationStoreProvider
```

更新后：

```python
@dataclass(frozen=True)
class ProvidersContainer:
    repository: ProjectRepositoryProvider
    storage: ProjectFileStorageProvider
    assets: GeneratedAssetProvider
    dataset: DatasetProvider
    regularization: RegularizationProvider
    regularization_store: RegularizationStoreProvider
    association_rules: AssociationRuleStoreProvider
    recommendation_models: RecommendationModelStoreProvider
    speech: SpeechSynthesisProvider
    llm: LLMProvider
    analysis_jobs: AnalysisJobProvider
    telemetry: TelemetryProvider
```

------

## 13.2 扩展 ProviderFactory

当前 `create_providers()` 在工厂中统一装配本地 Provider。

应新增：

```python
regularization=DefaultRegularizationProvider(...)
regularization_store=LocalRegularizationStoreAdapter("data")
```

这样正则化模块符合当前分支的依赖注入风格，而不是绕过 Provider 直接读写文件。

------

## 13.3 扩展 DatasetProvider

当前 `DatasetProvider` 提供 `load_dataset`、`load_project_dataset`、`load_default`、`resolve_default_path`、`save_dataset` 等能力。

建议扩展为：

```python
class DatasetProvider(Protocol):
    def load_dataset(self, path: Path) -> Any: ...
    def load_project_dataset(self, project_id: str) -> Any: ...
    def load_raw_project_dataset(self, project_id: str) -> Any: ...
    def load_normalized_project_dataset(self, project_id: str) -> Any: ...
    def save_normalized_dataset(self, project_id: str, rows: Any) -> None: ...
```

短期兼容方案：

```text
load_project_dataset(project_id)
    默认优先读 normalized/dataset.csv
    如果不存在，再回退到 data/projects/{project_id}/dataset.csv
```

这样可以减少一次性重构风险。

------

# 14. API 设计

当前项目 API 已经包含项目创建、上传、重新分析、下载报告、查看客户、查看音频、商品推荐等接口。上传接口会调用 `DatasetUploadPipeline.upload()` 并返回“文件上传成功，开始分析”。

建议新增正则化接口：

## 14.1 正则化预览

```http
POST /api/projects/{project_id}/regularization/preview
```

用途：

- 读取 raw 数据；
- 推断字段映射；
- 返回质量预览；
- 不真正提交分析。

返回：

```json
{
  "success": true,
  "mapping": {},
  "confidence": {},
  "need_review": [],
  "quality_summary": {},
  "preview_rows": []
}
```

## 14.2 确认字段映射

```http
POST /api/projects/{project_id}/regularization/confirm
```

用途：

- 用户确认或修改字段映射；
- 保存 `schema_mapping.json`。

## 14.3 执行正则化

```http
POST /api/projects/{project_id}/regularization/run
```

用途：

- 生成 normalized dataset；
- 生成质量报告；
- 生成 capability；
- 可选择是否随后触发分析。

## 14.4 获取质量报告

```http
GET /api/projects/{project_id}/regularization/report
```

## 14.5 获取分析能力

```http
GET /api/projects/{project_id}/regularization/capability
```

------

# 15. 上传流程改造方案

## 15.1 当前流程

```text
用户上传文件
    ↓
校验后缀
    ↓
保存 dataset.csv
    ↓
项目状态 = 处理中
    ↓
提交分析任务
```

## 15.2 建议新流程：自动正则化模式

```text
用户上传文件
    ↓
保存 raw 文件
    ↓
运行正则化 preview
    ↓
若字段映射高置信度，则自动正则化
    ↓
生成 normalized/dataset.csv
    ↓
项目状态 = 处理中
    ↓
提交分析任务
```

适合教学项目或演示环境，用户体验更顺畅。

## 15.3 建议新流程：人工确认模式

```text
用户上传文件
    ↓
保存 raw 文件
    ↓
运行正则化 preview
    ↓
前端展示字段映射
    ↓
用户确认
    ↓
生成 normalized/dataset.csv
    ↓
用户点击开始分析
```

适合真实业务场景，可靠性更高。

## 15.4 推荐实现方式

第一阶段先做“自动正则化 + 低置信度报错提示”：

```text
高置信度字段足够
    → 自动正则化并分析

关键字段低置信度
    → 项目状态仍为待确认
    → 前端提示用户确认字段映射
```

------

# 16. Project 模型扩展建议

当前 `Project` 模型包含项目 ID、名称、描述、数据集文件名、数据集路径、状态、分析参数、结果、错误信息、创建时间、更新时间。

建议新增字段：

```python
regularization_status: Optional[str] = None
raw_dataset_path: Optional[str] = None
normalized_dataset_path: Optional[str] = None
schema_mapping_path: Optional[str] = None
quality_report_path: Optional[str] = None
capability_path: Optional[str] = None
analysis_ready_score: Optional[float] = None
```

也可以先不改 Project 主模型，而将这些信息只存入 `manifest.json`，降低对现有 API 的影响。

推荐渐进方案：

| 阶段     | 做法                                                         |
| -------- | ------------------------------------------------------------ |
| 第一阶段 | 只用 manifest 文件，不改 Project 模型                        |
| 第二阶段 | Project 增加 `normalized_dataset_path` 和 `analysis_ready_score` |
| 第三阶段 | 前端展示完整正则化状态                                       |

------

# 17. 正则化模块内部类设计

## 17.1 RegularizationPipeline

```python
class RegularizationPipeline:
    def preview(self, project_id: str, raw_path: Path) -> RegularizationPreview:
        raw_df = self.reader.read(raw_path)
        profile = self.profiler.profile(raw_df)
        mapping = self.mapper.infer(raw_df, profile)
        quality_preview = self.quality_checker.preview(raw_df, mapping)
        return RegularizationPreview(...)

    def run(self, project_id: str, raw_path: Path, mapping: dict | None = None) -> RegularizationResult:
        raw_df = self.reader.read(raw_path)
        profile = self.profiler.profile(raw_df)
        mapping = mapping or self.mapper.infer(raw_df, profile)
        normalized_df = self.type_normalizer.normalize(raw_df, mapping)
        normalized_df = self.business_normalizer.normalize(normalized_df)
        quality = self.quality_checker.check(raw_df, normalized_df, mapping)
        capability = self.capability_checker.check(normalized_df)
        self.store.save_all(project_id, normalized_df, mapping, quality, capability)
        return RegularizationResult(...)
```

------

## 17.2 SchemaProfiler

负责生成字段画像：

```json
{
  "column": "销售日期",
  "dtype": "object",
  "missing_rate": 0.0,
  "n_unique": 180,
  "sample_values": ["20250101", "20250102"],
  "pattern": "yyyymmdd"
}
```

------

## 17.3 SchemaMapper

负责字段推断：

```json
{
  "raw_column": "顾客编号",
  "standard_field": "user_id",
  "confidence": 0.98,
  "source": "alias_exact_match"
}
```

------

## 17.4 TypeNormalizer

负责类型转换：

| 字段     | 转换     |
| -------- | -------- |
| 日期     | datetime |
| 金额     | float    |
| 数量     | float    |
| 单价     | float    |
| 促销     | int 0/1  |
| ID       | string   |
| 类目编码 | string   |

------

## 17.5 BusinessNormalizer

负责业务补全：

| 功能                 | 说明                               |
| -------------------- | ---------------------------------- |
| 生成 pseudo_order_id | 无订单号时构造购物篮键             |
| 金额数量单价互补     | 保证核心销售字段完整               |
| 单位归一             | 统一千克、袋、盒等                 |
| 退货标记             | 生成 `is_return`                   |
| 类目兜底             | 缺小类时使用商品 ID                |
| 商品显示名           | 用商品编码 + 类目生成 display name |

------

## 17.6 QualityChecker

负责质量报告：

```python
quality = {
    "row_count_raw": ...,
    "row_count_normalized": ...,
    "missing_rates": ...,
    "invalid_counts": ...,
    "repair_counts": ...,
    "analysis_ready_score": ...
}
```

------

## 17.7 CapabilityChecker

负责能力判断：

```python
capability = {
    "can_run_association": True,
    "can_run_customer_profile": True,
    "can_run_recommendation": True,
    "can_run_forecast": True,
    "can_run_promotion_analysis": True,
    "can_run_profit_analysis": False
}
```

------

# 18. 分析能力适配标准字段

正则化模块上线后，所有分析能力都应逐步从固定中文字段迁移到标准字段。

## 18.1 关联规则改造

当前：

```python
dataset.groupby("订单 ID")["子类别"].apply(list)
```

建议：

```python
basket_key = "order_id" if "order_id" in df.columns else "pseudo_order_id"

if "cat_l3_name" in df.columns:
    item_key = "cat_l3_name"
elif "cat_l2_name" in df.columns:
    item_key = "cat_l2_name"
else:
    item_key = "item_id"

basket = df[df["is_return"] == 0].groupby(basket_key)[item_key].apply(list)
```

------

## 18.2 顾客画像改造

当前依赖 `客户 ID`、`订单日期`、`订单 ID`、`销售额`。

建议统一改为：

```python
groupby("user_id")
sale_date
basket_key
amount
quantity
is_promo
unit_price
```

若缺少利润，不再让聚类失败，而是：

```text
profit_available = False
跳过利润率
用 amount 替代贡献指标
```

------

## 18.3 推荐模型改造

推荐模型统一读取：

```text
user_id
item_id
basket_key
cat_l1_name
cat_l2_name
cat_l3_name
amount
quantity
sale_date
is_promo
unit_price
```

如果部分字段缺失，则按 capability 降级。

------

# 19. 前端交互设计

## 19.1 数据正则化确认页面

上传数据后，进入“数据正则化”页面。

页面包括四部分：

```text
1. 数据读取结果
2. 字段映射确认
3. 数据质量报告
4. 可运行分析能力
```

## 19.2 字段映射表

| 原始字段 | 标准字段  | 置信度 | 状态   | 用户操作  |
| -------- | --------- | ------ | ------ | --------- |
| 顾客编号 | user_id   | 0.99   | 已确认 | 修改      |
| 销售日期 | sale_date | 0.96   | 已确认 | 修改      |
| 商品编码 | item_id   | 0.94   | 已确认 | 修改      |
| 是否促销 | is_promo  | 0.83   | 待确认 | 确认/修改 |

## 19.3 数据质量卡片

展示：

```text
数据行数
字段覆盖率
缺失率
异常金额数量
生成订单号数量
分析可用评分
```

## 19.4 分析能力卡片

| 分析能力   | 状态     | 说明                 |
| ---------- | -------- | -------------------- |
| 销售统计   | 可运行   | 核心字段完整         |
| 顾客画像   | 可运行   | 用户、日期、金额完整 |
| 关联规则   | 可运行   | 使用 pseudo_order_id |
| 个性化推荐 | 可运行   | 用户与商品字段完整   |
| 利润分析   | 不可运行 | 缺少利润字段         |

------

# 20. 测试方案

## 20.1 单元测试

| 模块               | 测试内容                             |
| ------------------ | ------------------------------------ |
| FileReader         | UTF-8、GBK、GB18030、Excel、多 Sheet |
| SchemaProfiler     | 字段类型、缺失率、唯一值、样本值     |
| SchemaMapper       | 字段别名、模糊匹配、低置信度         |
| TypeNormalizer     | 日期、金额、数量、促销               |
| BusinessNormalizer | pseudo_order_id、单价补全、退货标记  |
| QualityChecker     | 缺失率、异常率、质量评分             |
| CapabilityChecker  | 字段缺失下的能力判断                 |

## 20.2 集成测试数据集

| 数据集              | 目的                 |
| ------------------- | -------------------- |
| 标准中文字段数据    | 验证完整流程         |
| 英文字段数据        | 验证别名映射         |
| 无订单号数据        | 验证 pseudo_order_id |
| 无利润数据          | 验证利润分析降级     |
| 无促销字段数据      | 验证促销分析跳过     |
| GBK 编码数据        | 验证编码识别         |
| Excel 多 Sheet 数据 | 验证 Sheet 选择      |
| 日期混合格式数据    | 验证日期正则化       |
| 金额带货币符号数据  | 验证数值清洗         |
| 单位脏值数据        | 验证单位归一         |

------

# 21. 分阶段落地计划

## 第一阶段：最小可用正则化闭环

目标：上传后自动生成标准数据集。

完成内容：

```text
file_reader.py
schema_mapper.py
type_normalizer.py
business_normalizer.py
quality_checker.py
capability_checker.py
regularization_pipeline.py
local_regularization_store_adapter.py
```

输出：

```text
normalized/dataset.csv
schema_mapping.json
quality_report.json
capability.json
manifest.json
```

------

## 第二阶段：接入上传流程

改造 `DatasetUploadPipeline`：

```text
保存 raw dataset
    ↓
执行 regularization
    ↓
正则化成功后提交 analysis
```

此阶段可以先不做前端确认页，只要高置信度字段足够就自动运行。

------

## 第三阶段：分析能力标准字段适配

优先改造：

```text
association
clustering
recommendation
forecast
report
```

核心目标：

```text
不再硬编码 订单 ID / 客户 ID / 子类别 / 销售额
统一读取 user_id / basket_key / item_key / amount
```

------

## 第四阶段：前端确认页

实现：

```text
字段映射确认
质量报告展示
能力状态展示
手动重新映射
重新正则化
```

------

## 第五阶段：智能字段识别增强

加入：

```text
字段名模糊匹配
值模式识别
映射模板复用
低置信度人工确认
历史映射记忆
```

------

# 22. 进一步完善建议

除了基础正则化，本模块还可以继续完善以下能力。

## 22.1 模板记忆机制

用户第一次上传某类数据时确认字段映射，系统保存模板：

```text
template_name = "某超市POS系统导出模板"
```

下次上传相同结构数据时自动套用。

## 22.2 正则化版本管理

每次正则化生成版本：

```text
regularization_version = v1
regularization_version = v2
```

允许用户回滚或对比：

```text
raw dataset
normalized v1
normalized v2
```

## 22.3 数据漂移检测

如果同一个项目多次上传数据，比较：

```text
字段是否变化
类目是否变化
金额分布是否变化
用户数量是否异常变化
商品数量是否异常变化
```

防止用户误上传错误文件。

## 22.4 隐私与脱敏

对手机号、姓名、会员卡号等字段进行识别和脱敏：

```text
手机号 → phone_hash
姓名 → name_hash
```

推荐模块只使用匿名 ID。

## 22.5 错误分级

错误不应全部变成“分析失败”，应区分：

| 错误等级    | 示例               | 处理                 |
| ----------- | ------------------ | -------------------- |
| warning     | 缺少利润字段       | 降级分析             |
| recoverable | 缺少订单号         | 生成 pseudo_order_id |
| blocking    | 缺少用户和商品字段 | 阻止推荐分析         |
| fatal       | 文件无法读取       | 上传失败             |

------

# 23. 最终推荐方案

基于当前 `add-analysis-2` 分支，建议将数据正则化模块定义为：

> **MarketMind Data Regularization Engine**
> 即 MarketMind 数据正则化引擎。

它不是简单的数据清洗脚本，而是一个产品级中间层。

最终结构应为：

```text
用户上传数据
    ↓
DatasetUploadPipeline 保存 raw 文件
    ↓
RegularizationPipeline 执行正则化
    ↓
生成 normalized dataset + mapping + quality + capability + manifest
    ↓
ProjectAnalysisFlow 读取 normalized dataset
    ↓
根据 capability 有选择运行分析能力
    ↓
输出消费者推荐与营销者报告
```

------

# 24. 模块建设价值总结

该模块建成后，MarketMind 将获得以下提升：

1. **从固定模板分析升级为通用数据分析**
   不再要求用户必须上传固定字段名的数据。
2. **显著降低分析失败率**
   字段缺失时可降级，而不是直接失败。
3. **提高用户信任度**
   用户能看到字段如何映射、数据如何修复、哪些分析可运行。
4. **提高后续算法可维护性**
   分析算法统一依赖标准字段，减少重复兼容逻辑。
5. **增强项目工程完整度**
   形成“上传—正则化—质量检查—能力判断—分析”的完整闭环。
6. **承接当前分支已有成果**
   当前 `analysis/code_files/data_preprocessing.py` 中的字段映射、单位归一、日期修正、促销二值化等经验可以作为算法原型；当前 Provider / Pipeline / Flow 架构可以作为模块集成基础；当前 CRITIC、TOPSIS、熵权等工具可以继续用于质量评分与分析能力评价。
