# 超市 AI 营销系统 SRS

## 1. Introduction

### 1.1 Purpose

本文档定义“超市 AI 营销系统”的软件需求。系统以新版 `analysis/` 的处理逻辑为业务基础，将离线实验流程重建为后端可调用、可测试、可扩展的 Python 服务。

本 SRS 用于指导后续后端逻辑重写、API 设计、测试设计和验收。

### 1.2 Scope

系统面向超市销售明细数据，提供：

- 数据清洗与质量诊断。
- 顾客画像、商品画像、复购周期和价格带分析。
- 商品关联规则和高效用组合挖掘。
- 顾客分群与群体营销策略。
- 消费者侧个性化推荐。
- 销售趋势预测和经营趋势分析。
- 营销者侧因果分析、发券建议、流失预测、CLV、价格弹性和品类经营洞察。
- 分析报告、表格、图表、模型 artifact 的后端化管理。

系统不包含：

- TTS / 语音播报 / 音频生成。
- 命令行脚本作为正式运行入口。
- 旧版 Superstore 分析逻辑兼容。

### 1.3 Definitions

| Term | Definition |
|---|---|
| Retail V2 | 新版 `analysis/` 定义的超市销售明细分析逻辑。 |
| Raw sales dataset | 原始销售 CSV，包含中文字段和 GBK 编码可能性。 |
| Clean dataset | 标准化后的内部明细表，使用 `user_id`、`item_id`、`cat_l3_code` 等字段。 |
| Basket | 按顾客和销售日期合并形成的购物清单集。 |
| HUIM | High Utility Itemset Mining，高效用项集挖掘。 |
| DML | Double Machine Learning，用于估计去偏促销因果效应。 |
| Artifact | 后端生成的 CSV、PNG、Markdown、JSON、模型引用等产物。 |
| Ability Atom | 后端四层架构中的最小业务动作。 |
| Business Pipeline | 编排多个 Ability Atom 的业务阶段。 |
| Business Flow | 管理多 Pipeline 长生命周期的业务流程。 |

## 2. Overall Description

### 2.1 Product Perspective

系统是 MarketMind 后端的新版核心分析能力。它应替代旧的简化分析逻辑，把 `analysis/` 中已验证的处理思想转化为服务端架构。

目标架构：

```text
API Controller -> RetailAnalysisFlow -> Retail Pipelines -> Retail Abilities -> Provider Interfaces -> External Adapters
```

### 2.2 User Classes

| User Class | Needs |
|---|---|
| IT 经理 | 可靠的数据接入、后端任务调度、错误可追踪、artifact 可管理。 |
| 营销经理 | 促销组合、发券名单、客群策略、商品推荐、品类策略。 |
| 门店管理层 | 经营摘要、销售趋势、客户价值、行动优先级。 |
| 数据分析师 | 模型指标、参数、算法输出、可复现实验结果。 |
| 前端系统 | 稳定 API、结构化响应、artifact 引用。 |

### 2.3 Operating Environment

- Python backend based on FastAPI.
- Data processing based on pandas / numpy / scikit-learn / mlxtend / statsmodels and approved optional analysis dependencies.
- Local or configured file storage for datasets, artifacts and model files.
- No TTS runtime requirement.

### 2.4 Design Constraints

- 后端运行代码不得直接 import `analysis/code_files/*.py`。
- 不允许把脚本 `main()` 作为 API 或 Pipeline 的运行入口。
- Ability Atom 不得读写文件、读取 env、依赖 FastAPI 对象或创建 Adapter。
- Pipeline 不得直接使用 pandas IO、pickle IO、matplotlib save path 或外部 SDK client。
- Provider Interface 不得依赖具体 Adapter。
- External Adapter 不得反向依赖 API / Business / Ability。
- TTS 相关能力不在本需求范围内。

## 3. Data Requirements

### 3.1 Raw Dataset Fields

系统应接收包含以下字段的超市销售明细：

| Field | Meaning |
|---|---|
| 顾客编号 | 顾客唯一标识。 |
| 大类编码 / 大类名称 | 一级类目编码和名称。 |
| 中类编码 / 中类名称 | 二级类目编码和名称。 |
| 小类编码 / 小类名称 | 三级类目编码和名称。 |
| 销售日期 | 交易日期。 |
| 销售月份 | 交易月份。 |
| 商品编码 | 商品唯一标识。 |
| 规格型号 | 商品规格。 |
| 商品类型 | 商品类型，例如一般商品、生鲜、联营商品。 |
| 单位 | 商品单位。 |
| 销售数量 | 销售数量。 |
| 销售金额 | 销售金额。 |
| 商品单价 | 商品单价。 |
| 是否促销 | 是否促销。 |

### 3.2 Clean Dataset Fields

系统应产出以下内部字段：

```text
user_id, cat_l1_code, cat_l1_name, cat_l2_code, cat_l2_name,
cat_l3_code, cat_l3_name, sale_date, sale_month, item_id,
spec, item_type, unit, quantity, amount, unit_price,
is_promo, is_return, weekday, is_weekend, week_of_year
```

### 3.3 Data Quality Rules

系统应：

- 删除完全重复行。
- 修复可识别的错位行。
- 标记 `quantity <= 0` 或 `amount <= 0` 为退货/异常交易。
- 将“是/否”促销字段映射为 `1/0`。
- 统一单位脏值，例如 KG/kg/公斤/散称 -> 千克。
- 填补规格空白为“未知规格”。
- 对单价为 0 或异常的记录使用同商品、同小类或全局中位数策略修复。
- 派生 weekday、is_weekend、week_of_year。
- 输出数据质量报告。

## 4. Functional Requirements

### FR-1 Dataset Upload And Preparation

The system shall accept a Retail V2 sales CSV and create a project-scoped analysis dataset.

Acceptance criteria:

- 支持 GBK 和 UTF-8-SIG 编码。
- 缺少必填字段时返回结构化 validation error。
- 生成 clean dataset artifact。
- 生成数据质量 summary artifact。
- 不写入 `analysis/output`。

### FR-2 Feature Engineering

The system shall build customer, product and repurchase features from the clean dataset.

Acceptance criteria:

- 生成 customer profile，包含 RFM、类目偏好、促销敏感度、价格偏好、退货率、生鲜占比、类目熵。
- 生成 product profile，包含销售金额、销售数量、购买人数、复购率、价格带、促销率、热度得分。
- 生成 repurchase cycle，包含用户-小类复购周期和复购紧迫度。
- 使用 CRITIC/TOPSIS 或等价方式生成可解释综合得分。

### FR-3 Customer Segmentation

The system shall segment customers and produce marketing-ready group profiles.

Acceptance criteria:

- 支持 GMM、UMAP+HDBSCAN、AE+GMM 思想的后端实现路线。
- 输出群体标签、人数、R/F/M、促销敏感度、生鲜占比、类目熵、低价带偏好、销售贡献。
- 输出群体价值排序。
- 输出每个群体的营销策略建议。

### FR-4 Association Rules And Bundle Promotion

The system shall mine basket-level association rules and high-utility itemsets.

Acceptance criteria:

- 按顾客和销售日期构建购物篮。
- 支持 item、小类、中类层级规则。
- 输出前项、后项、支持度、置信度、提升度。
- 支持按后项商品查询促销带动规则。
- 输出 HUIM 组合，包含总效用、篮均效用、支持度、效用占比。
- 输出组合促销策略建议。

### FR-5 Consumer Recommendation

The system shall generate explainable Top-K product recommendations.

Acceptance criteria:

- 支持热门、类目偏好、关联规则、图嵌入、复购周期、促销适配、价格偏好等信号。
- 使用融合排序输出最终推荐。
- 每条推荐包含 item、category、score、source signals、reason。
- 输出推荐评估指标：Precision、Recall、HitRate、NDCG、Coverage、Diversity、PromoMatchRate。

### FR-6 Sales Forecast And Trend Analysis

The system shall forecast sales trends and produce operation-oriented trend artifacts.

Acceptance criteria:

- 按日或业务设定粒度聚合销售金额和相关经营指标。
- 支持季节分解、ACF/PACF、Holt-Winters 或等价时序预测。
- 输出预测表、回测指标和趋势图 artifact。
- 数据不足时返回明确错误。

### FR-7 Promotion Causal Analysis

The system shall estimate the true effect of promotions after controlling confounders.

Acceptance criteria:

- 输出朴素均值差与 DML 去偏 ATE 对比。
- 输出按顾客群体的 CATE。
- 输出置信区间或等价不确定性度量。
- 标记真正正响应促销的人群。
- 不把外部模型异常直接返回给 API 用户。

### FR-8 Marketer Insight

The system shall produce marketer-facing strategy outputs.

Acceptance criteria:

- 输出群体价值排序。
- 输出组合促销策略。
- 输出促销响应/发券建议。
- 输出品类经营象限和策略。
- 输出结构化 marketer insight DTO 和 Markdown/JSON artifact。

### FR-9 Advanced Analytics

The system should support advanced analytics when dependencies and runtime checks are available.

Capabilities:

- LightGCN recommendation.
- Uplift coupon targeting.
- Churn prediction.
- CLV prediction.
- Price elasticity.
- Robustness and Monte Carlo validation.

Acceptance criteria:

- 高阶能力不得阻塞基础分析链路。
- 缺少 optional dependency 时返回 capability unavailable，而不是后端启动失败。

### FR-10 API And Project Lifecycle

The system shall expose backend APIs for project creation, dataset upload, analysis execution, status query and result retrieval.

Required endpoints:

| Endpoint | Description |
|---|---|
| `POST /api/analysis/projects` | Create analysis project. |
| `POST /api/analysis/projects/{id}/dataset` | Upload Retail V2 dataset. |
| `POST /api/analysis/projects/{id}/run` | Start RetailAnalysisFlow. |
| `GET /api/analysis/projects/{id}` | Get status and summary. |
| `GET /api/analysis/projects/{id}/artifacts` | List generated artifacts. |
| `GET /api/analysis/projects/{id}/recommendations` | Get consumer recommendations. |
| `GET /api/analysis/projects/{id}/marketer-insights` | Get marketer insights. |

### FR-11 Artifact Management

The system shall save and expose generated analysis artifacts.

Acceptance criteria:

- Artifacts include clean dataset, quality report, profiles, rules, recommendations, marketer insights, charts and reports.
- Artifact references are project-scoped.
- Runtime artifacts are not written to `analysis/output`.
- API returns artifact metadata, not raw local implementation paths.

### FR-12 Excluded TTS

The system shall not include TTS in this requirement scope.

Acceptance criteria:

- No voice synthesis API is required for Retail V2.
- No audio artifact is required.
- No edge-tts dependency is required by the new analysis flow.

## 5. Non-Functional Requirements

### NFR-1 Architecture

- System shall follow API Controller -> Business Flow/Pipeline -> Ability -> Provider -> Adapter.
- Architecture Lint shall prevent backend runtime imports from `analysis/code_files`.
- Business layers shall not call filesystem, external SDK clients or env readers directly.

### NFR-2 Reliability

- Each pipeline stage shall report success/failure status.
- Failure shall include stage name and internal error type.
- Partial artifact writes shall not be exposed as completed results.

### NFR-3 Performance

- Core analysis shall run on a 42k-row dataset without requiring manual command-line operation.
- Heavy model training should be staged or optional if it materially increases runtime.
- The system should support background execution for full RetailAnalysisFlow.

### NFR-4 Security And Privacy

- Uploaded datasets shall be project-scoped.
- API errors shall not leak local filesystem paths, raw stack traces or external SDK response bodies.
- Generated artifacts shall be accessible only through approved API/static paths.

### NFR-5 Observability

- Flow and pipeline stages shall emit telemetry events.
- Telemetry shall include project id, stage, status, artifact summary and error type.
- Secret-like fields and raw customer data shall not be logged.

### NFR-6 Testability

- Ability Atom tests shall use small deterministic fixtures.
- Pipeline tests shall use fake providers and `tmp_path`.
- Provider adapter tests shall verify encoding, IO, artifact and model behavior.
- API tests shall verify request/response schema and error format.

## 6. External Interface Requirements

### 6.1 API Response Principles

Responses shall be JSON and include:

- `success` or equivalent status.
- `message`.
- `project_id` when project-scoped.
- `stage_status` for long-running analysis.
- `data` or typed result object.
- `artifacts` when generated.
- Structured error object for failures.

### 6.2 Artifact Metadata

Artifact metadata shall include:

- `artifact_id`.
- `project_id`.
- `kind`.
- `name`.
- `mime_type` or data type.
- `created_at`.
- `size` when available.
- `url` or API-resolvable reference.

## 7. Acceptance Plan

Minimum acceptance commands:

```bash
uv run pytest tests/abilities/retail
uv run pytest tests/business/test_retail_*_pipeline.py
uv run pytest tests/providers/test_*retail*.py tests/providers/test_*analysis*.py
uv run pytest tests/api/test_retail_analysis_contracts.py
uv run pytest tests/test_architecture_imports.py
uv run python -m backend.core.runtime_checks check-retail-analysis --sample tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv
make lint
make check
make hooks
```

If full lint is blocked by unrelated legacy debt, the blocker must be recorded separately and must not be mixed into the Retail V2 implementation commit.

## 8. Traceability Matrix

| Original Requirement | SRS Coverage |
|---|---|
| 制定某些商品的促销策略，合并订单记录形成购物清单，找出商品作为后项的关联规则。 | FR-4, FR-8 |
| 预测未来销售额和利润。 | FR-6 |
| 对客户聚类分析，制定针对性营销策略。 | FR-3, FR-8 |
| 使用新版 analysis 逻辑。 | FR-1 through FR-9 |
| 后端可调用，不保留命令行脚本。 | FR-10, NFR-1 |
| TTS 不需要。 | FR-12 |
