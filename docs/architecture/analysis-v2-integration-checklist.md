# Analysis V2 Backend Construction Checklist

本清单用于把新版 `analysis/` 的处理逻辑重建为后端可调用的 Python 架构实现。新版 `analysis` 是目标逻辑来源；旧分析逻辑不再作为兼容目标。

执行规则：

- 必须从第一个未完成任务开始。
- 每次只执行一个内聚阶段。
- 未建立行为保护前，不允许迁移或删除旧代码。
- 新实现必须进入 `backend/` 四层架构，不保留命令行脚本式运行路径。
- `analysis/code_files/*.py` 只能作为蓝本，不得被 API / Pipeline / Ability 直接 import。
- `STATUS` 只使用 `pending`、`in_progress`、`completed`、`blocked`。`blocked` 必须写解除条件。

## Current Execution Notes

- 2026-05-25: 已拉取并切换到 `add-analysis-2`，执行 `rm -rf analysis && mv analysis_2 analysis`。
- 2026-05-25: 已按新版 `analysis` 作为唯一目标逻辑重写设计和清单。
- 当前未执行后端代码迁移，未新增 runtime dependency，未提交 API replacement。

## 0. Ready-to-Start Gate

### [x] Replace old analysis directory with analysis_2

- WHERE: `analysis/`, `analysis_2/`.
- WHY: 用户指定新版 `analysis` 作为后续处理逻辑基线。
- HOW: 执行 `rm -rf analysis` 后 `mv analysis_2 analysis`。
- EXPECTED_RESULT: 工作区中存在新版 `analysis/`，不再存在 `analysis_2/`。
- VERIFY: `find . -maxdepth 2 -type d -name 'analysis*' -print`
- STATUS: completed
- RESULT: 当前只看到 `./analysis`；`analysis_2` 已被移除。
- RISK: 新版 `analysis/README.md` 仍写 `analysis_2/`，后续 cleanup 修正。
- ROLLBACK: `git restore analysis analysis_2`。

### [x] Set target behavior to Analysis V2 only

- WHERE: `docs/architecture/analysis-v2-integration-design.md`, this checklist.
- WHY: 用户明确要直接使用新版 `/analysis` 文档和处理思想。
- HOW: 将设计表述改为“旧后端只提供架构壳参考，新逻辑重建为后端四层实现”。
- EXPECTED_RESULT: 后续任务以 Retail V2 为目标，不再围绕旧 Superstore 逻辑设计。
- VERIFY: `rg -n "新版.*唯一目标|Retail V2.*目标|不保留命令行脚本" docs/architecture/analysis-v2-integration-*.md`
- STATUS: completed
- RESULT: 文档已改为以新版 Retail V2 分析逻辑为唯一目标。
- RISK: 旧前端/API 若仍在使用，需要后续单独设计 UI/API replacement，而不是兼容迁移。
- ROLLBACK: 回退本次文档修改。

### [x] Produce design and checklist before code migration

- WHERE: `docs/architecture/analysis-v2-integration-design.md`, `docs/architecture/analysis-v2-integration-checklist.md`.
- WHY: Skill 门禁要求未产出架构文档和施工清单前不得改迁移代码。
- HOW: 建立专门文档，明确不保留 CLI 脚本，改造成后端 Ability / Pipeline / Provider / Adapter。
- EXPECTED_RESULT: 后续实现可以按阶段推进，并能独立验证、独立回滚。
- VERIFY: `git status --short docs/architecture/analysis-v2-integration-design.md docs/architecture/analysis-v2-integration-checklist.md`
- STATUS: completed
- RESULT: 两个文档已重写；当前仍未迁移后端代码。
- RISK:
- ROLLBACK: 删除或回退两个文档。

## 1. 测试锚点

### [ ] Add Retail V2 raw dataset fixture

- WHERE: `tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv`.
- WHY: 新后端逻辑以新版 `analysis/data/销售数据.csv` 字段为唯一数据契约，需要小型可执行 fixture。
- HOW: 从大 CSV 抽取最小样本，覆盖正常销售、退货、促销、单位脏值、错位行、单价 0、规格空白。
- EXPECTED_RESULT: 测试不依赖大文件，也能锁定清洗边界。
- VERIFY: `uv run pytest tests/abilities/retail/test_clean_retail_sales.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add clean dataset contract tests

- WHERE: `tests/abilities/retail/test_clean_retail_sales.py`.
- WHY: 所有后续能力依赖 clean schema。
- HOW: 断言 clean 字段、dtype、日期派生、促销映射、退货标记、单位归一、错误语义。
- EXPECTED_RESULT: raw -> clean 行为先被测试固定。
- VERIFY: `uv run pytest tests/abilities/retail/test_clean_retail_sales.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add algorithm fixture tests for core Analysis V2 outputs

- WHERE: `tests/abilities/retail/`.
- WHY: 新版逻辑复杂，必须先用小数据保护特征、规则、推荐、因果、营销洞察的可观察输出。
- HOW: 分别为 feature engineering、association、recommendation、promotion DML、marketer insights 添加 deterministic tests。
- EXPECTED_RESULT: 每个核心 Ability 迁移前有最小行为锚点。
- VERIFY: `uv run pytest tests/abilities/retail`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add Retail API contract tests

- WHERE: `tests/api/test_retail_analysis_contracts.py`.
- WHY: 旧 API 不再是目标，必须为新版后端 API 定义新契约。
- HOW: 先测试新路由的请求 schema、响应 schema、状态流转、错误格式、artifact refs。
- EXPECTED_RESULT: 后续替换 controller 时以新 API contract 为准。
- VERIFY: `uv run pytest tests/api/test_retail_analysis_contracts.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 2. Provider Interface

### [ ] Define RetailDatasetProvider

- WHERE: `backend/providers/retail_dataset_provider.py`, `backend/providers/dtos.py`.
- WHY: GBK/raw retail CSV、schema validation、clean dataset persistence 属于外部数据访问边界。
- HOW: 定义 load_raw_sales、save_clean_sales、load_clean_sales、validate_raw_schema 等窄接口和 DTO。
- EXPECTED_RESULT: Pipeline 不直接使用 pandas IO 或文件路径。
- VERIFY: `uv run python -m py_compile backend/providers/retail_dataset_provider.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Define AnalysisArtifactProvider

- WHERE: `backend/providers/analysis_artifact_provider.py`, `backend/providers/dtos.py`.
- WHY: 新逻辑会产生 CSV、PNG、Markdown、JSON summary，业务层不得写 `analysis/output`。
- HOW: 定义 save_table、save_figure、save_markdown、save_json、resolve_artifact，返回 artifact refs。
- EXPECTED_RESULT: 分析产物由 Provider Boundary 管理。
- VERIFY: `uv run python -m py_compile backend/providers/analysis_artifact_provider.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Define AnalysisModelStoreProvider

- WHERE: `backend/providers/analysis_model_store_provider.py`.
- WHY: 聚类、推荐、uplift、LightGCN、CLV 等模型产物不能把 pickle/joblib/torch 细节泄漏给业务层。
- HOW: 定义 typed save/load/list/delete model artifact 接口；先覆盖核心模型。
- EXPECTED_RESULT: 模型持久化由 Adapter 实现，Pipeline 只处理 model ref。
- VERIFY: `uv run python -m py_compile backend/providers/analysis_model_store_provider.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 3. External Adapter

### [ ] Implement CsvRetailDatasetAdapter

- WHERE: `backend/infrastructure/adapters/csv_retail_dataset_adapter.py`.
- WHY: 新版 raw CSV 是 GBK 且字段为中文业务字段。
- HOW: Adapter 处理编码、文件读取、schema validation、clean dataset 保存；捕获 pandas IO 错误并转为内部错误。
- EXPECTED_RESULT: 后端可从上传文件读取 Retail V2 数据。
- VERIFY: `uv run pytest tests/providers/test_csv_retail_dataset_adapter.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Implement LocalAnalysisArtifactAdapter

- WHERE: `backend/infrastructure/adapters/local_analysis_artifact_adapter.py`.
- WHY: 后端 runtime 产物必须落在项目隔离目录或配置目录，不写 `analysis/output`。
- HOW: 使用 Settings 注入 base dir，保存 table/figure/markdown/json 并返回 DTO。
- EXPECTED_RESULT: artifact refs 可被 API 返回和审计。
- VERIFY: `uv run pytest tests/providers/test_local_analysis_artifact_adapter.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Implement LocalAnalysisModelStoreAdapter

- WHERE: `backend/infrastructure/adapters/local_analysis_model_store_adapter.py`.
- WHY: v2 模型文件需要统一存取和清理。
- HOW: 隐藏 pickle/joblib/torch 序列化细节，支持 model type/version/project id。
- EXPECTED_RESULT: Pipeline 不直接 open/write pkl。
- VERIFY: `uv run pytest tests/providers/test_local_analysis_model_store_adapter.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Decide and wire heavy dependencies

- WHERE: `pyproject.toml`, `backend/infrastructure/factories/provider_factory.py`.
- WHY: LightGBM、Torch、UMAP、HDBSCAN、SHAP、Lifetimes 影响安装、CI 和启动。
- HOW: 决定 default dependencies 或 optional groups；任何 optional SDK 不得在默认 import path 缺失时报错。
- EXPECTED_RESULT: 核心后端可启动，高阶能力有 capability check。
- VERIFY: `uv run pytest tests/core/test_runtime_checks.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 4. Ability Atom

### [ ] Extract retail cleaning abilities

- WHERE: `backend/abilities/retail/normalize_unit.py`, `repair_shifted_sales_rows.py`, `clean_retail_sales.py`.
- WHY: `data_preprocessing.py` 混合字段映射、清洗、IO、图表；后端需要纯能力。
- HOW: 输入 raw DataFrame，输出 clean DataFrame + quality summary DTO；不得写文件或画图。
- EXPECTED_RESULT: 清洗能力可被 Pipeline 调用和单测。
- VERIFY: `uv run pytest tests/abilities/retail/test_clean_retail_sales.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Extract feature engineering abilities

- WHERE: `backend/abilities/retail/build_customer_profile.py`, `build_product_profile.py`, `build_repurchase_cycle.py`, `rank_by_critic_topsis.py`.
- WHY: 顾客画像、商品画像、复购周期和 CRITIC/TOPSIS 是新版分析核心基础。
- HOW: 迁移纯算法，返回 DataFrame/DTO，不保存 CSV。
- EXPECTED_RESULT: Pipeline 可组合画像和复购结果。
- VERIFY: `uv run pytest tests/abilities/retail/test_feature_engineering.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Extract segmentation abilities

- WHERE: `backend/abilities/retail/cluster_retail_customers.py`.
- WHY: 新逻辑以 GMM/HDBSCAN/AE+GMM 代替旧 KMeans 简化分群。
- HOW: 先实现可稳定测试的 GMM/HDBSCAN，AE+GMM 视依赖和耗时单独阶段。
- EXPECTED_RESULT: 输出群体标签、群体画像、模型指标和贡献度。
- VERIFY: `uv run pytest tests/abilities/retail/test_retail_segmentation.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Extract association and HUIM abilities

- WHERE: `backend/abilities/retail/mine_retail_association_rules.py`, `mine_high_utility_itemsets.py`.
- WHY: 新逻辑使用 FP-Growth 和高效用项集作为组合营销基础。
- HOW: 提取事务构建、规则筛选、中文字段输出、HUIM 计算。
- EXPECTED_RESULT: 输出 rules、rule metrics、bundle candidates。
- VERIFY: `uv run pytest tests/abilities/retail/test_retail_association.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Extract recommendation abilities

- WHERE: `backend/abilities/retail/build_retail_recommendation_signals.py`, `rank_retail_recommendations.py`, optional `train_graph_recommender.py`.
- WHY: 新逻辑使用多召回 + CRITIC-TOPSIS，不再沿用旧分群偏好推荐。
- HOW: 先迁移非 Torch 的 SVD/规则/类目/复购/促销信号；LightGCN 独立 gated。
- EXPECTED_RESULT: 输出用户 Top-K、score breakdown、推荐理由。
- VERIFY: `uv run pytest tests/abilities/retail/test_retail_recommendation.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Extract marketer and causal abilities

- WHERE: `backend/abilities/retail/estimate_promotion_effect.py`, `estimate_customer_uplift.py`, `build_marketer_insights.py`.
- WHY: DML、uplift、群体价值、组合促销和品类策略是新版营销者侧核心。
- HOW: 提取 DML ATE/CATE、DR-learner、segment value、bundle strategy、category operation。
- EXPECTED_RESULT: 输出结构化 marketer insight DTO。
- VERIFY: `uv run pytest tests/abilities/retail/test_marketer_insights.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 5. Business Pipeline

### [ ] Add RetailDatasetPreparationPipeline

- WHERE: `backend/business/pipelines/retail_dataset_preparation_pipeline.py`.
- WHY: 数据读取、清洗、质量报告、clean artifact 是业务阶段，不属于单个 ability。
- HOW: 编排 RetailDatasetProvider、cleaning abilities、AnalysisArtifactProvider。
- EXPECTED_RESULT: raw CSV 变成 clean dataset artifact 和 quality summary。
- VERIFY: `uv run pytest tests/business/test_retail_dataset_preparation_pipeline.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add RetailFeatureEngineeringPipeline

- WHERE: `backend/business/pipelines/retail_feature_engineering_pipeline.py`.
- WHY: 多个画像与复购能力有顺序依赖。
- HOW: 编排 price rank、customer profile、product profile、repurchase cycle，并保存 artifact refs。
- EXPECTED_RESULT: 产出后续分群/推荐/营销决策所需特征。
- VERIFY: `uv run pytest tests/business/test_retail_feature_engineering_pipeline.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add RetailSegmentationPipeline

- WHERE: `backend/business/pipelines/retail_segmentation_pipeline.py`.
- WHY: 新版分群是核心用户画像阶段。
- HOW: 编排 segmentation abilities、模型存储、segment artifact。
- EXPECTED_RESULT: 产出 segment labels、profiles、metrics、model ref。
- VERIFY: `uv run pytest tests/business/test_retail_segmentation_pipeline.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add RetailAssociationPipeline

- WHERE: `backend/business/pipelines/retail_association_pipeline.py`.
- WHY: 关联规则和 HUIM 是推荐和营销策略输入。
- HOW: 编排 FP-Growth、HUIM、rule metrics、artifact writes。
- EXPECTED_RESULT: 产出 item/category rules 和 bundle candidates。
- VERIFY: `uv run pytest tests/business/test_retail_association_pipeline.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add RetailRecommendationPipeline

- WHERE: `backend/business/pipelines/retail_recommendation_pipeline.py`.
- WHY: 多召回和融合排序需要维护中间信号、权重、候选池、理由。
- HOW: 编排 recommendation abilities、model store、artifact provider。
- EXPECTED_RESULT: 产出消费者侧推荐结果和模型/权重 artifacts。
- VERIFY: `uv run pytest tests/business/test_retail_recommendation_pipeline.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add RetailMarketerInsightPipeline

- WHERE: `backend/business/pipelines/retail_marketer_insight_pipeline.py`.
- WHY: 营销者侧需要组合 segment、rules、DML、category strategy。
- HOW: 编排 marketer abilities，生成结构化 insight DTO 和 report input。
- EXPECTED_RESULT: 产出群体价值、促销响应、组合策略、品类象限。
- VERIFY: `uv run pytest tests/business/test_retail_marketer_insight_pipeline.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add RetailReportPipeline

- WHERE: `backend/business/pipelines/retail_report_pipeline.py`.
- WHY: Markdown/报告是 pipeline result 的渲染，不应由实验脚本直接写文件。
- HOW: 将结构化 results 渲染为 Markdown/JSON summary，并通过 AnalysisArtifactProvider 保存。
- EXPECTED_RESULT: 报告生成可测试、可审计、可 API 引用。
- VERIFY: `uv run pytest tests/business/test_retail_report_pipeline.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 6. Business Flow

### [ ] Build RetailAnalysisFlow

- WHERE: `backend/business/flows/retail_analysis_flow.py`.
- WHY: 新版分析是多阶段长生命周期，需要统一状态、错误、artifact/model refs。
- HOW: 编排 Dataset Preparation、Feature、Segmentation、Association、Recommendation、Marketer、Report pipelines；记录每阶段 telemetry。
- EXPECTED_RESULT: 一次项目分析可由后端任务调度并完整产出新版结果。
- VERIFY: `uv run pytest tests/business/test_retail_analysis_flow.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 7. API Controller

### [ ] Add Retail Analysis API contract

- WHERE: `backend/api/analysis.py`, `backend/models/schemas.py`.
- WHY: 旧 API 不再是目标，需要为新版分析建立清晰入口。
- HOW: 定义 create project、upload dataset、run analysis、get status、list artifacts、get recommendations、get marketer insights。
- EXPECTED_RESULT: Controller 只做 schema 与 pipeline/flow 调用。
- VERIFY: `uv run pytest tests/api/test_retail_analysis_contracts.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Route Retail API in FastAPI app

- WHERE: `backend/main.py`.
- WHY: 新 API 需要注册到 app。
- HOW: include router with `/api/analysis` prefix；确保 controller 不直接使用 pandas/sklearn/file IO。
- EXPECTED_RESULT: OpenAPI schema 包含新版分析 endpoints。
- VERIFY: `uv run python -m backend.core.runtime_checks validate-api-schemas`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Remove or retire old analysis endpoints after replacement

- WHERE: `backend/api/projects.py`, `backend/api/recommend.py`, `backend/api/association.py`, docs.
- WHY: 用户明确不需要兼容旧逻辑，最终应避免双系统长期并存。
- HOW: 在新 API tests 通过后，删除或标记旧入口退役；同步前端/API 文档。
- EXPECTED_RESULT: 后端主路径只服务新版 Retail V2 分析。
- VERIFY: `uv run pytest tests/api/test_retail_analysis_contracts.py && uv run pytest tests/test_architecture_imports.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 8. Architecture Lint / Runtime Check / 全量验证

### [ ] Extend Architecture Lint for retail modules

- WHERE: `tests/test_architecture_imports.py`.
- WHY: 新增 retail modules 后必须防止脚本式依赖回流。
- HOW: 禁止 backend import `analysis.code_files`; 禁止 abilities/pipelines 直接 import os env、FastAPI、infrastructure、SDK IO；禁止 providers import adapters。
- EXPECTED_RESULT: 架构边界机械化保护新版实现。
- VERIFY: `uv run pytest tests/test_architecture_imports.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Add Retail runtime checks

- WHERE: `backend/core/runtime_checks.py`, `tests/core/test_runtime_checks.py`.
- WHY: 新版流程需要验证配置、Provider 装配、sample dry-run、artifact/model root。
- HOW: 新增 `check-retail-analysis --sample ...`、`check-analysis-artifacts --sandbox`、`check-analysis-optional-runtime`。
- EXPECTED_RESULT: 后端运行事实可验证，不依赖命令行脚本。
- VERIFY: `uv run pytest tests/core/test_runtime_checks.py`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Run quality gates per stage

- WHERE: repository root.
- WHY: 每阶段必须可独立验证。
- HOW: 先 touched-scope，再 full gate；如果 full lint 被既有债务阻塞，记录为债务，不混进当前 commit。
- EXPECTED_RESULT: 每阶段都有验证证据。
- VERIFY: `make lint`, `make format`, `make lint`, `make check`, `make hooks`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

## 9. 清理与收尾

### [ ] Update analysis documentation after directory rename

- WHERE: `analysis/README.md`, `analysis/code_files/project_plan.md`.
- WHY: 当前文本仍可能写 `analysis_2/`。
- HOW: 改为 `analysis/`，并标明该目录是算法蓝本/参考，不是后端 runtime 入口。
- EXPECTED_RESULT: 后续 agent 不会误用旧路径或命令行脚本。
- VERIFY: `rg -n "analysis_2|python .*exp_|__main__" analysis docs/architecture`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Decide generated artifact repository policy

- WHERE: `analysis/output/`, `.gitignore`, docs.
- WHY: 新版包含 CSV/PNG/PKL generated outputs，不应和后端 runtime artifact 混淆。
- HOW: 决定保留为 reference、迁入 fixtures、或 ignore regenerated outputs。
- EXPECTED_RESULT: 代码评审和运行产物边界清楚。
- VERIFY: `git status --short analysis/output`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:

### [ ] Delete retired legacy backend paths

- WHERE: `backend/services/*`, old abilities/pipelines/api endpoints as applicable.
- WHY: 新版逻辑成为主路径后，不应长期保留旧逻辑造成双重真相。
- HOW: 在 Retail API / Flow / tests 通过后删除未使用旧代码；更新 docs。
- EXPECTED_RESULT: 后端只有新版 Analysis V2 主链路。
- VERIFY: `uv run pytest tests/test_architecture_imports.py && make check`
- STATUS: pending
- RESULT:
- RISK:
- ROLLBACK:
