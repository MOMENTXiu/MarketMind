# MarketMind 需求分析书

## 1. 项目概述

MarketMind 是我们小组开发并开源的 AI 营销分析系统，面向零售销售明细数据和通用交易类数据的分析场景。系统通过前后端分离方式提供数据上传、数据标准化、质量检查、客户分群、商品关联分析、个性化推荐、促销效果分析、营销洞察和文本建议等能力，帮助将原始业务数据转化为可执行的营销决策依据。

当前主应用采用 Vue 3 + FastAPI 架构。前端提供 Retail Analysis V2 和 Data Processing 两条使用流程；后端通过 `/api/analysis` 统一承载项目、任务、数据集、分析产物、推荐结果、营销洞察和文本建议接口。

## 2. 项目背景

零售经营中，促销组合、客户触达、商品推荐、客户分群和经营策略制定通常依赖经验判断。原始销售数据往往存在字段不统一、编码差异、脏值、异常交易、缺失信息和分析结果分散等问题，导致业务人员难以及时获得可解释、可复用、可落地的营销建议。

本项目希望把数据清洗、分析建模和结果展示整合为一套可运行的系统：对固定中文列零售 CSV 提供完整 Retail Analysis V2 分析链路；对字段不固定的通用 CSV/Excel 数据提供标准化和通用分析链路；并通过后端 LLM Provider 提供客户营销建议与商品洞察文本。系统不包含 TTS、语音播报或音频生成能力。

## 3. 建设目的

1. 降低零售数据分析门槛，使用户能够通过上传数据获得结构化分析结果、图表、报告和业务建议。
2. 支持零售场景中的客户分群、商品关联、个性化推荐、促销效果分析和营销洞察输出。
3. 支持字段不固定的通用业务数据先标准化、再分析，提升系统对不同数据源的适应能力。
4. 建立清晰的前后端和后端分层边界，使系统具备可测试、可维护和可扩展的工程基础。
5. 以开源项目形式交付，提供 README、架构文档、接口文档、使用指南、项目计划和质量门命令。

## 4. 用户角色

| 角色 | 主要诉求 |
| --- | --- |
| IT 经理 | 关注系统建设、数据接入、后端任务执行、错误可追踪、接口稳定性和交付质量。 |
| 营销经理 | 关注客户分群、促销组合、商品推荐、发券建议、客户触达和经营洞察。 |
| 门店管理层 | 关注经营摘要、客户结构、商品表现、营销策略优先级和行动建议。 |
| 数据分析师 | 关注数据质量、模型输出、分析指标、结果解释和可复现实验依据。 |
| 前端系统 | 需要稳定 API、结构化响应、状态跟踪、产物引用和错误语义。 |

## 5. 业务范围

### 5.1 范围内

1. Retail Analysis V2：面向固定中文列零售 CSV，支持项目创建、数据上传、数据准备、分析任务、阶段状态、推荐结果、营销洞察和 artifact 引用。
2. Data Processing：面向通用 CSV/Excel，支持 Job 创建、原始数据上传、标准化、quality/capability/sidecars、通用分析和 outputs 查询。
3. AI 文本建议：通过后端 `POST /api/analysis/customer-suggestions` 生成客户营销建议与商品洞察文本。
4. 前端工作台：提供首页、项目介绍页、项目空间、数据处理、推荐与客户分析相关页面。
5. 本地基础设施：通过 Docker Compose 提供 PostgreSQL、Redis 和 MinIO，用于状态、队列、事件和对象存储等运行能力。
6. 工程质量：通过 Makefile、Ruff、pytest、前端 build 和 pre-commit 形成质量门。

### 5.2 范围外

1. TTS、语音播报、音频生成和语音相关接口。
2. 已退役旧接口 `/api/projects`、`/api/recommend`、`/api/association` 的兼容恢复。
3. 直接将命令行脚本作为正式运行入口。
4. 后端运行时直接 import `analysis/code_files` 或 `analysis/data-processing-pipeline` 中的归档代码。
5. 在未确认依赖和运行条件前，把高级实验能力作为基础链路的强制前置条件。

## 6. 功能需求

### 6.1 Retail Analysis V2

1. 系统应支持创建、查询、删除零售分析项目。
2. 系统应支持上传固定中文列零售 CSV，并进行数据准备。
3. 系统应校验 Retail V2 必要字段，字段以项目代码中的 `RETAIL_RAW_SALES_COLUMNS` 及文档说明为准。
4. 系统应支持运行零售分析任务，并返回 `queued`、`processing`、`completed`、`failed` 等状态。
5. 系统应输出质量摘要、阶段状态、分析摘要、artifact refs、推荐结果和营销洞察。
6. 系统应支持通过 REST snapshot 获取状态，并通过 SSE 事件作为正常状态更新路径。

### 6.2 Data Processing

1. 系统应支持创建数据处理 Job。
2. 系统应支持上传 `.csv`、`.xls` 或 `.xlsx` 格式的通用数据文件。
3. 系统应执行 `raw dataset upload -> regularization -> analysis2 universal analysis -> output refs` 流程。
4. 系统应输出 schema mapping、quality report、capability、manifest、preview rows 等 sidecars。
5. 当 core 字段需要复核时，系统应进入 `needs_review` 状态并阻断后续 run。
6. 当 optional/marketing 字段映射不完整时，不应阻断通用分析。
7. 当数据缺少共购结构时，association 阶段可以 `skipped`，Job 仍可完成。

### 6.3 AI 文本建议

1. 系统应通过后端 `POST /api/analysis/customer-suggestions` 提供文本建议能力。
2. 前端业务页面不得直接调用第三方 `/chat/completions` 或 `/models` 接口。
3. 当真实 LLM 调用不可用时，业务层可返回 deterministic fallback 文本。
4. 生产环境真实模型配置开放前，应补充服务端密钥管理、鉴权和审计能力。

### 6.4 前端功能

1. 系统应提供首页、项目介绍、项目空间和数据处理入口。
2. Retail 页面应支持项目创建、上传数据、启动分析、查看状态和查看结果。
3. Data Processing 页面应支持 Job 创建、上传数据、标准化、运行分析和查看 outputs/sidecars。
4. 服务状态组件应调用后端健康检查接口展示服务可用性。
5. 前端业务请求应通过 `frontend/src/api/` 中的 typed API client 统一访问后端。

### 6.5 后端接口

1. 后端应提供健康检查、OpenAPI 文档、样本文件、Retail 项目、Data Processing Job、artifact、dataset、model ref 和文本建议等接口。
2. `/api/analysis` 下的业务接口应保持结构化响应和明确错误语义。
3. 业务错误应映射为可判断的 HTTP 状态码和错误信息。
4. 已退役接口不得作为兼容入口重新引入。

## 7. 非功能需求

### 7.1 可维护性

后端应保持 `API Controller -> Business Flow/Pipeline -> Ability Atom -> Provider Interface -> Infrastructure Adapter` 分层架构。API 层不写算法或存储细节；Business 层不直接依赖数据库、Redis、外部 SDK 或本地绝对路径；Provider Interface 不依赖具体 Adapter。

### 7.2 可测试性

项目应通过测试覆盖 API、业务流、能力原子、Provider、Infrastructure、DB 和架构导入规则。质量门以 Makefile 中实际目标为准，核心包括 `make lint`、`make format`、`make check` 和 `make hooks`。

### 7.3 可扩展性

存储、任务队列、事件流、LLM、artifact、模型产物等能力应通过 Provider Boundary 隔离，便于替换 PostgreSQL、Redis、MinIO、本地文件系统或 LLM Provider。

### 7.4 可用性

系统应提供清晰的前端入口和状态展示。长任务应能展示任务状态，失败时应提供可判断错误信息，前端应具备 REST 状态兜底能力。

### 7.5 安全性

当前项目文档将生产环境鉴权、API key 管理、服务端 LLM 密钥托管和审计列为下一阶段重点。待确认：正式部署时的用户认证方式、权限模型和密钥管理方案。

## 8. 数据需求

### 8.1 Retail V2 数据

Retail V2 当前接受固定中文列 CSV。字段包括：

```text
顾客编号,大类编码,大类名称,中类编码,中类名称,小类编码,小类名称,销售日期,销售月份,商品编码,规格型号,商品类型,单位,销售数量,销售金额,商品单价,是否促销
```

本地冒烟数据位于：

```text
tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv
```

### 8.2 Data Processing 数据

Data Processing 接受通用 `.csv`、`.xls`、`.xlsx` 文件。系统会通过 regularization 流程生成字段映射、质量报告、能力判断和标准化数据集。字段无法满足 core 映射要求时进入 `needs_review`。

### 8.3 产物数据

分析产物包括表格、JSON、Markdown、图表、报告、模型引用、sidecars 和 dataset refs。大文件、图表、报告和模型 artifact 不应直接塞入 PostgreSQL，应通过文件系统、MinIO 或 Provider ref/API URL 暴露。

## 9. 验收标准

| 评价项 | 验收标准 | 权重 |
| --- | --- | ---: |
| 核心业务功能完整性 | Retail Analysis V2 能完成项目创建、CSV 上传、分析运行、状态查询、质量摘要、产物引用、推荐结果和营销洞察；Data Processing 能完成 Job 创建、CSV/Excel 上传、标准化、outputs/sidecars 查询；AI 文本建议通过后端接口提供。 | 35% |
| 数据处理与分析结果可用性 | 系统能完成必要的数据清洗、标准化、质量检查和能力判断；异常、数据不足或字段需复核时返回可判断状态或错误信息。 | 20% |
| 架构与接口规范 | 后端分层边界符合项目架构要求；前端通过 `frontend/src/api/` 调用后端；业务接口以 `/api/analysis` 为主；退役接口不恢复。 | 15% |
| 前端体验与状态展示 | 前端提供 Retail 和 Data Processing 主要工作流；任务状态、失败状态、needs_review 和服务状态可判断。 | 10% |
| 工程质量 | `make lint`、`make format`、`make check` 能按项目配置执行；提交前执行 `make hooks`；占位目标不得作为验证通过依据。 | 15% |
| 文档与开源交付 | README、架构文档、接口文档、使用指南、需求材料、项目计划、环境说明和 MIT License 齐备。 | 5% |

合计：100%

## 10. 假定与约束

### 10.1 项目假定

1. 使用者能够提供符合业务场景的数据文件，Retail V2 使用固定中文列 CSV，Data Processing 使用通用 CSV/Excel。
2. 本地开发环境具备 Python 3.13、uv、Node.js 18+ 和 npm。
3. 完整本地运行可使用 Docker Compose 启动 PostgreSQL、Redis 和 MinIO。
4. LLM 文本建议依赖可配置的后端 Provider；真实生产配置开放前需要补充密钥托管、鉴权和审计。
5. `analysis/` 目录是离线实验、算法蓝本和迁移源材料归档，不是后端 runtime 直接依赖。

### 10.2 项目约束

1. 本项目为我们小组开发并开源的项目，不描述为二次开发项目。
2. 后端不得直接 import 归档算法目录中的运行逻辑。
3. Business 层不得直接依赖 SQLAlchemy、Redis client、外部 SDK 或本地绝对路径。
4. Redis 只承载任务队列和事件流，不作为业务真相源。
5. 大 CSV、图表、报告、模型 artifact 不直接写入 PostgreSQL。
6. 前端业务页面必须通过 typed API client 调用后端。
7. TTS、语音播报和音频生成不属于当前范围。
8. `make typecheck` 和 `make clean` 当前为占位目标，不能作为验证通过依据。

## 11. 依据来源

- `README.md`：项目定位、当前能力、技术栈、目录结构和质量门。
- `docs/requirements/software-requirements-specification.md`：业务需求、数据字段、功能范围和设计约束。
- `docs/requirements/user-story.md`：用户角色、Epic、验收条件和范围外内容。
- `docs/ARCHITECTURE.md`：运行架构、API surface、Retail/Data Processing 流程、前端 API 边界和基础设施说明。
- `docs/USAGE_GUIDE.md`：使用流程、数据要求、状态含义和产物入口。
- `docs/backend-api.md`：后端接口契约和错误语义。
- `docs/PROJECT_PLAN.md`：当前基线、核心目标、后续路线和红线。
- `pyproject.toml`、`frontend/package.json`、`docker-compose.dev.yml`、`Makefile`：技术栈、依赖、基础设施和验证命令。
