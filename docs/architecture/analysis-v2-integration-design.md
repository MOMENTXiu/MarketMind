# Analysis V2 Backend Architecture Design

## 1. Scope

本文件规划如何把新版 `analysis/` 的处理思想改造成后端可调用的 Python 架构实现。新版 `analysis/` 是目标业务逻辑来源；旧后端分析逻辑不再作为兼容目标，只作为可复用的四层架构壳、已有 Provider / Pipeline 模式和测试组织参考。

本次已按用户要求完成目录替换：

```text
rm -rf analysis
mv analysis_2 analysis
```

关键决策：

- 不需要兼容旧 Superstore 分析逻辑。
- 不保留命令行脚本式 `main()` 作为后端运行入口。
- 不让 API Controller、Business Pipeline 或 Ability 直接 import `analysis/code_files/*.py`。
- 必须按新版 `analysis` 的数据清洗、特征工程、分群、关联、推荐、营销决策、因果分析思路，在 `backend/` 内重建可测试、可注入、可由 API 调用的 Python 实现。
- 原 `analysis/code_files/*.py` 只作为算法和业务规则蓝本；最终运行代码应落在 `backend/abilities`、`backend/business`、`backend/providers`、`backend/infrastructure`。

目标方向：

```text
API Controller -> Business Flow -> Business Pipeline -> Ability Atom -> Provider Interface -> External Adapter
```

新版分析是多阶段、长耗时、有中间产物和模型产物的生命周期，因此允许使用 Business Flow；单个算法动作仍必须拆为 Ability Atom。

## 2. Current Backend Assets To Reuse

当前后端已有可复用架构基础：

| Layer | Reusable Paths | Reuse Strategy |
|---|---|---|
| API Controller | `backend/api/*.py` | 保留 FastAPI 路由组织方式，但后续 endpoint/response 可改为服务新版分析逻辑。 |
| Business Orchestration | `backend/business/pipelines/*`, `backend/business/flows/project_analysis_flow.py` | 复用 Pipeline / Flow 写法，新增或替换为 Retail V2 分析链路。 |
| Ability Layer | `backend/abilities/*` | 复用“纯业务动作 + 显式输入输出”的拆分方式，新增 `backend/abilities/retail/*`。 |
| Provider Boundary | `backend/providers/*`, `backend/providers/container.py` | 复用 Provider Container 模式，扩展 retail dataset、artifact、model store。 |
| Infrastructure | `backend/infrastructure/adapters/*`, `backend/infrastructure/factories/provider_factory.py` | 复用 Adapter / Factory 模式，新增 CSV/GBK、artifact、model 适配器。 |
| Tests | `tests/abilities`, `tests/business`, `tests/providers`, `tests/api`, `tests/test_architecture_imports.py` | 复用测试分层方式，为新逻辑建立行为锚点。 |

旧分析能力，如 KMeans RFM、Apriori、旧字段预测和旧推荐逻辑，不再是行为等价目标。后续可删除、替换或降级为历史参考，但删除前仍需通过新逻辑测试和 API 契约测试保护。

## 3. Analysis V2 Source Inventory

新版 `analysis/` 的业务处理链路：

```text
raw GBK sales csv
  -> data_preprocessing
  -> feature_engineering
  -> exp_clustering
  -> exp_association
  -> exp_recommendation
  -> exp_marketer
  -> optional advanced analysis:
       exp_lightgcn, exp_uplift, exp_churn, exp_timeseries,
       exp_clv, exp_elasticity_robust, exp_montecarlo
```

核心模块：

| Source Module | Business Logic To Rebuild In Backend |
|---|---|
| `data_preprocessing.py` | GBK 原始超市销售数据清洗、错位行修复、单位归一、退货标记、促销字段映射、质量报告。 |
| `feature_engineering.py` | 顾客画像、商品画像、价格分位、复购周期、复购紧迫度、CRITIC/TOPSIS 热度。 |
| `exp_clustering.py` | GMM、UMAP+HDBSCAN、AE+GMM 分群、群体命名、群体画像、贡献度。 |
| `exp_association.py` | FP-Growth、小类/中类/item 规则、高效用项集 HUIM、组合促销候选。 |
| `exp_recommendation.py` | 多召回、图嵌入 SVD、规则/类目/复购/促销信号、CRITIC-TOPSIS 融合排序、推荐理由。 |
| `exp_marketer.py` | 群体价值排序、组合促销、DML 促销因果、品类经营象限、营销策略报告。 |
| `causal_dml.py` | DML ATE/CATE 工具、组间异质处理效应。 |
| `exp_lightgcn.py` | LightGCN 图推荐，作为高阶推荐能力。 |
| `exp_uplift.py` | DR-learner 发券 uplift 和发券名单。 |
| `exp_churn.py` | 流失预测和 SHAP 解释。 |
| `exp_timeseries.py` | 日销售时序分解、ACF/PACF、Holt-Winters 回测。 |
| `exp_clv.py` | BG/NBD + Gamma-Gamma CLV。 |
| `exp_elasticity_robust.py` | 价格弹性、规则显著性、聚类稳定性。 |
| `exp_montecarlo.py` | 合成真值还原验证，应优先迁为测试/Runtime Check。 |

## 4. Target Data Contract

新版后端以 Retail V2 数据契约为目标，不再兼容旧字段作为主路径。

Raw input fields:

```text
顾客编号, 大类编码, 大类名称, 中类编码, 中类名称, 小类编码, 小类名称,
销售日期, 销售月份, 商品编码, 规格型号, 商品类型, 单位,
销售数量, 销售金额, 商品单价, 是否促销
```

Clean internal fields:

```text
user_id, cat_l1_code, cat_l1_name, cat_l2_code, cat_l2_name,
cat_l3_code, cat_l3_name, sale_date, sale_month, item_id,
spec, item_type, unit, quantity, amount, unit_price,
is_promo, is_return, weekday, is_weekend, week_of_year
```

Backend rule:

- API / Pipeline 只接受 Retail V2 数据契约。
- Dataset Adapter 负责 GBK/UTF-8-SIG 读取和 raw schema validation。
- Ability 负责业务清洗、特征计算和模型逻辑。
- Pipeline 负责阶段顺序、中间结果、artifact/model 持久化和错误语义。

## 5. Infrastructure And Boundary Problems In Source Scripts

新版脚本当前是离线脚本形态，进入后端前必须拆除这些耦合：

| Problem | Current Location | Backend Treatment |
|---|---|---|
| Hard-coded local path | `config.py` uses `ROOT = r"D:\new_Marketmind"` | 删除运行时依赖；改为 `Settings -> Provider Factory -> Adapter config`。 |
| Import-time side effects | `config.py` import 时 `os.makedirs` | 移入 Adapter 初始化或 Pipeline 显式 artifact 写入。 |
| Script `main()` orchestration | Every `exp_*.py` | 不保留命令行主流程；重建为 Business Pipeline / Flow。 |
| Direct CSV/PKL/PNG IO | `save_csv`, `save_pkl`, `savefig`, `pd.read_csv` | 移入 Dataset / Artifact / Model Store Adapter。 |
| Plot generation inside algorithms | Matplotlib mixed with model logic | 拆成 plot Ability 或 Artifact Adapter 接收 figure bytes/path。 |
| Heavy dependency imports in default path | Torch, LightGBM, UMAP, HDBSCAN, SHAP, Lifetimes | 明确进入默认依赖或 optional analysis extra；默认后端 import 不应在缺依赖时崩溃。 |
| Generated output as source truth | `analysis/output/*` | 不作为后端 source of truth；仅作为参考产物或 fixture 来源。 |

## 6. Target Backend Architecture

### 6.1 Business Flow

新增或替换为：

```text
RetailAnalysisFlow
  -> RetailDatasetPreparationPipeline
  -> RetailFeatureEngineeringPipeline
  -> RetailSegmentationPipeline
  -> RetailAssociationPipeline
  -> RetailRecommendationPipeline
  -> RetailMarketerInsightPipeline
  -> RetailAdvancedAnalyticsPipeline (optional / staged)
  -> RetailReportPipeline
```

Flow responsibilities:

- 管理项目状态：queued / processing / completed / failed。
- 记录每个阶段状态、错误、artifact refs、model refs。
- 保证失败时有内部错误映射和可观察状态。
- 不直接实现算法。

### 6.2 Business Pipelines

| Pipeline | Responsibility |
|---|---|
| `RetailDatasetPreparationPipeline` | raw CSV load、schema validation、clean dataset、quality summary。 |
| `RetailFeatureEngineeringPipeline` | customer profile、product profile、price rank、repurchase cycle。 |
| `RetailSegmentationPipeline` | GMM / HDBSCAN / AE+GMM 分群与群体画像。 |
| `RetailAssociationPipeline` | FP-Growth 规则、HUIM、组合促销候选。 |
| `RetailRecommendationPipeline` | 多召回候选、信号可靠性、CRITIC-TOPSIS 排序、推荐理由。 |
| `RetailMarketerInsightPipeline` | segment value、promotion DML、bundle strategy、category operation。 |
| `RetailAdvancedAnalyticsPipeline` | uplift、churn、time series、CLV、elasticity、LightGCN，按依赖成熟度分阶段进入。 |
| `RetailReportPipeline` | 汇总结构化结果为后端报告 DTO / Markdown / artifact refs。 |

### 6.3 Ability Atoms

Initial ability package:

```text
backend/abilities/retail/
  normalize_unit.py
  repair_shifted_sales_rows.py
  clean_retail_sales.py
  compute_price_rank.py
  build_customer_profile.py
  build_product_profile.py
  build_repurchase_cycle.py
  rank_by_critic_topsis.py
  cluster_retail_customers.py
  mine_retail_association_rules.py
  mine_high_utility_itemsets.py
  build_retail_recommendation_signals.py
  rank_retail_recommendations.py
  estimate_promotion_effect.py
  estimate_customer_uplift.py
  predict_customer_churn.py
  forecast_retail_sales.py
  estimate_customer_lifetime_value.py
  estimate_price_elasticity.py
```

Ability rules:

- 输入是 DataFrame / DTO / primitive config，输出是 DTO / DataFrame / serializable structure。
- 不读取 env。
- 不创建 Adapter。
- 不写文件。
- 不依赖 FastAPI request/response。
- 不 import `analysis.code_files.config` 或 `analysis.code_files.exp_*`。

### 6.4 Provider Boundary

Required providers:

| Provider | Purpose |
|---|---|
| `RetailDatasetProvider` | raw retail CSV load/save, encoding handling, raw schema validation, clean dataset persistence. |
| `AnalysisArtifactProvider` | 保存 CSV、PNG、Markdown、JSON summary，并返回 artifact refs。 |
| `AnalysisModelStoreProvider` | 保存/读取 typed model artifacts，隐藏 pickle/joblib/torch 序列化细节。 |
| `TelemetryProvider` | 记录阶段、错误、trace、artifact summary。 |
| Existing `ProjectRepositoryProvider` | 存项目状态和分析结果摘要。 |
| Existing `AnalysisJobProvider` | 调度 RetailAnalysisFlow。 |

Adapter candidates:

```text
backend/infrastructure/adapters/csv_retail_dataset_adapter.py
backend/infrastructure/adapters/local_analysis_artifact_adapter.py
backend/infrastructure/adapters/local_analysis_model_store_adapter.py
```

## 7. API Direction

旧 API 不再是兼容约束。后端 API 应围绕新版 Retail V2 分析能力重新整理。

Recommended endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /api/analysis/projects` | 创建新版分析项目。 |
| `POST /api/analysis/projects/{id}/dataset` | 上传 Retail V2 原始销售 CSV，并触发或准备分析。 |
| `POST /api/analysis/projects/{id}/run` | 启动完整 RetailAnalysisFlow。 |
| `GET /api/analysis/projects/{id}` | 获取项目状态、阶段状态、核心摘要。 |
| `GET /api/analysis/projects/{id}/artifacts` | 获取 CSV/图/报告/model artifact refs。 |
| `GET /api/analysis/projects/{id}/recommendations` | 获取消费者侧推荐结果。 |
| `GET /api/analysis/projects/{id}/marketer-insights` | 获取营销者侧策略洞察。 |

Controller only:

- request schema validation。
- 调用 Flow / Pipeline。
- response schema mapping。
- internal error -> public error mapping。

Controller must not:

- 调用 pandas / sklearn / torch / matplotlib。
- 读写 CSV/PKL/PNG。
- import `analysis/code_files`。
- 编排多个算法步骤。

## 8. Error Strategy

| Scenario | Internal Error |
|---|---|
| Missing raw retail fields | `ValidationError` |
| CSV encoding/read failure | `InfrastructureError` from `RetailDatasetProvider` adapter |
| Cleaning cannot repair malformed rows | `PipelineExecutionError` |
| Insufficient data for model | `PipelineExecutionError` with stage name |
| Optional dependency missing | `ProviderError` with actionable dependency/profile message |
| Artifact write failure | `InfrastructureError` from artifact adapter |
| Model serialization failure | `InfrastructureError` from model store adapter |

External exceptions from pandas IO, sklearn, mlxtend, matplotlib, torch, LightGBM, SHAP, HDBSCAN, UMAP, Lifetimes, pickle/joblib must be converted before crossing Provider / Pipeline boundaries.

## 9. Test And Runtime Strategy

Behavior protection should target the new logic, not old behavior compatibility:

```bash
uv run pytest tests/abilities/retail
uv run pytest tests/business/test_retail_*_pipeline.py
uv run pytest tests/providers/test_*analysis*.py tests/providers/test_*retail*.py
uv run pytest tests/api/test_retail_analysis_contracts.py
uv run pytest tests/test_architecture_imports.py
uv run python -m backend.core.runtime_checks check-retail-analysis --sample tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv
make lint
make check
make hooks
```

Runtime checks should cover:

- Settings and artifact/model base directories。
- Provider Factory can assemble Retail V2 providers。
- raw CSV sample can be loaded and cleaned。
- RetailAnalysisFlow dry-run on small fixture。
- artifact refs are created under sandbox path。
- optional dependencies report capability status without crashing default runtime。

## 10. Migration Strategy

Migration should replace backend business behavior in controlled stages:

1. Add new test fixtures and contracts for Retail V2。
2. Add Provider Interfaces and Adapters。
3. Extract pure Ability Atoms from `analysis/code_files` logic。
4. Build Pipelines around the abilities。
5. Build RetailAnalysisFlow。
6. Replace / add API endpoints for new analysis contracts。
7. Remove old analysis/recommendation code paths once new API tests pass。
8. Clean docs, generated artifacts, and dependency groups。

Important: do not port scripts by copying `main()` bodies. Each script must be decomposed into explicit abilities and pipelines.

## 11. Open Implementation Decisions

| Decision | Default Recommendation |
|---|---|
| Should old project/recommend endpoints remain? | They may remain temporarily during transition, but are not compatibility targets. Final API should serve Retail V2 logic. |
| Should LightGCN/SHAP/HDBSCAN/Lifetimes be default dependencies? | Decide per phase. Default should not import missing optional dependencies at module import time. |
| Should `analysis/output` be committed? | Treat as reference artifacts only; backend runtime writes to project-scoped artifact storage. |
| Should report output remain Markdown? | Yes as an artifact format, but source should be structured DTO -> report renderer, not script-side file writing. |

## 12. Rollback Strategy

Planning phase rollback:

```text
git restore docs/architecture/analysis-v2-integration-design.md
git restore docs/architecture/analysis-v2-integration-checklist.md
git restore analysis analysis_2
```

Implementation rollback should be stage-based:

- Tests: remove only Retail V2 tests/fixtures.
- Providers: remove Retail provider files and container fields.
- Adapters: remove Retail adapter files and factory wiring.
- Abilities: remove `backend/abilities/retail/*`.
- Pipelines/Flow: remove `retail_*_pipeline.py` and `retail_analysis_flow.py`.
- API: remove Retail V2 endpoints and route registration.

## 13. Current Risks

| Risk | Required Action |
|---|---|
| `analysis/README.md` still says `analysis_2/`. | Update during cleanup after design acceptance. |
| `config.py` hard-codes Windows path and creates dirs at import. | Do not import it from backend; extract constants/logic into Settings and adapters. |
| Source scripts mix algorithms, plotting, file IO, and orchestration. | Split into Ability, Pipeline, Adapter, Report Renderer. |
| Heavy dependencies are not declared. | Add dependency strategy before advanced abilities enter backend runtime. |
| Generated CSV/PNG/PKL artifacts are currently in source tree. | Decide reference vs ignored generated output before committing large churn. |
