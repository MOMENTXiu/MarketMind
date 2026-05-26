# MarketMind 使用指南

## 系统架构说明

MarketMind 已重构为**项目管理模式**，采用 Vue3 + FastAPI 前后端分离架构。

### 核心功能

1. **项目管理**：创建、管理和分析多个营销数据项目
2. **关联规则分析**：基于 Apriori 算法的购物篮分析
3. **销售预测**：项目分析流程中的时间序列预测能力
4. **客户聚类**：项目分析流程中的 RFM + K-Means 客户分群能力
5. **AI 文本建议**：生成客户营销建议和商品洞察文本

## 快速开始

### 1. 启动后端服务

```bash
# 在项目根目录执行
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将运行在：http://localhost:8000

API 文档地址：http://localhost:8000/api/docs

### 2. 启动前端服务

```bash
# 进入前端目录
cd frontend

# 首次运行需要安装依赖（已完成可跳过）
npm install

# 启动开发服务器
npm run dev
```

前端服务将运行在：http://localhost:5173

## 使用流程

### 第一步：访问首页

打开浏览器访问 http://localhost:5173

首页会显示：
- ✅ 后端连接状态检查
- ➕ 新建项目按钮
- 📋 我的项目按钮
- 四大功能模块介绍卡片

### 第二步：新建项目

1. 点击"➕ 新建项目"或"📋 我的项目"按钮
2. 进入项目列表页
3. 点击"➕ 新建项目"开始创建

#### 多步表单流程：

**步骤 1：项目信息**
- 填写项目名称（必填）
- 填写项目描述（可选）

**步骤 2：上传数据 & 设置参数**
- 上传 CSV 或 Excel 数据集文件
- 设置分析参数（可选）：
  - 最小支持度（默认 2%）
  - 最小置信度（默认 30%）
  - 最小提升度（默认 1.0）
  - 预测周数（默认 13 周）
  - 聚类数量（默认 4 类）

**步骤 3：确认创建**
- 确认项目信息和参数
- 点击"创建并开始分析"

### 第三步：查看项目详情

创建成功后会自动跳转到项目详情页，页面包含：

#### 1. 项目信息卡片
- 项目名称、数据集、创建时间
- 项目状态：待处理 / 处理中 / 已完成 / 失败
- 操作按钮：重新分析、下载报告

#### 2. 关联规则分析（已完成时显示）
- Top 10 关联规则列表
- 显示前项、后项、支持度、置信度、提升度
- 营销策略建议

#### 3. 销售预测
- 预测周数设置
- 未来销售额和利润预测图表

#### 4. 客户聚类
- RFM 模型分析
- K-Means 聚类结果
- 客户分群特征

#### 5. AI 文本建议
- 客户详情页自动生成营销建议
- 商品关联页生成商业洞察文本
- 设置页配置 LLM 服务

## 项目状态说明

- **待处理**：项目已创建，但数据集未上传
- **处理中**：正在执行数据分析（页面会自动刷新）
- **已完成**：分析完成，可查看结果
- **失败**：分析过程中出现错误

## 数据集要求

### 文件格式
- 当前 runtime：CSV 文件
- 后续通用链路：正则化引擎设计支持 CSV / Excel，但尚未接入后端 runtime

### 当前 Retail V2 CSV 字段

当前后端 runtime 只支持 Retail V2 CSV。字段契约以代码为准：
`backend/providers/dtos.py` 中的 `RETAIL_RAW_SALES_COLUMNS`。

### 示例数据

可使用测试夹具进行本地冒烟：

```bash
tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv
```

### 后续通用链路

`analysis/data-processing-pipeline/` 已归档新的通用数据处理源材料：
`regularization/` 负责任意数据正则化，`analysis2/` 负责基于标准 Schema
与 capability 的通用分析。该链路尚未接入后端 runtime，施工方案见
`docs/architecture/data-processing-pipeline-integration-design.md`。

## API 接口说明

### 项目管理
- `POST /api/analysis/projects` - 创建 Retail V2 分析项目
- `GET /api/analysis/projects` - 获取分析项目列表
- `GET /api/analysis/projects/{id}` - 获取项目详情
- `DELETE /api/analysis/projects/{id}` - 删除项目

### 文件上传
- `POST /api/analysis/projects/{id}/dataset` - 上传 Retail V2 CSV 并完成数据准备

### 分析操作
- `POST /api/analysis/projects/{id}/run` - 启动或复用分析任务
- `GET /api/analysis/projects/{id}` - 获取项目详情、阶段状态、summary 与 refs

### 结果读取
- `GET /api/analysis/projects/{id}/recommendations` - 获取 Retail V2 推荐结果
- `GET /api/analysis/projects/{id}/marketer-insights` - 获取营销者洞察
- `GET /api/analysis/projects/{id}/artifacts/{artifact_id}` - 解析分析产物引用
- `GET /api/analysis/projects/{id}/datasets/{dataset_id}` - 解析数据集引用
- `GET /api/analysis/projects/{id}/models/{model_type}/{version}` - 解析模型引用

## 目录结构

```
MarketMind/
├── backend/                 # 后端 FastAPI 服务
│   ├── api/                # HTTP 薄控制器
│   ├── business/           # Pipeline / Flow 编排层
│   ├── abilities/          # 原子分析与生成能力
│   ├── providers/          # Provider Interface / DTO / Container
│   ├── infrastructure/     # 本地文件、LLM、Telemetry 等 Adapter
│   ├── core/               # 配置、内部错误、runtime checks
│   ├── models/             # 项目模型和 API schemas
│   └── main.py             # 应用入口
├── frontend/              # 前端 Vue3 应用
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   │   ├── Home.vue           # 首页
│   │   │   ├── ProjectList.vue    # 项目列表
│   │   │   ├── ProjectCreate.vue  # 新建项目
│   │   │   ├── ProjectDetail.vue  # 项目详情
│   │   │   └── MyProjects.vue     # 我的项目
│   │   ├── router/       # 路由配置
│   │   └── main.ts       # 应用入口
│   └── package.json
├── data/                  # 数据存储目录
│   ├── projects.json     # 项目元数据
│   └── projects/         # 项目文件夹
│       └── {project_id}/
│           └── analysis/      # Retail V2 runtime 数据集、产物、模型
└── analysis/              # Analysis V2 算法蓝本 + data-processing pipeline 归档
```

## 开发状态

### ✅ 已完成
- 项目管理系统
- 关联规则分析（Apriori 算法）
- AI 文本建议（LLM）
- 前后端架构重构
- 多步表单创建流程
- 项目详情页面
- Retail V2 清洗、特征工程、分群、关联/HUIM、推荐、营销洞察 Ability
- 业务 Pipeline / RetailAnalysisFlow / Provider Adapter 分层
- Data-processing pipeline 源材料归档和迁移方案（未接入 runtime）

## 技术栈

### 后端
- Python 3.13
- FastAPI 0.123.5
- Pydantic 2.12.5
- pandas, numpy, scikit-learn
- mlxtend (Apriori)
- httpx (LLM HTTP adapter)

### 前端
- Vue 3.5.13
- TypeScript 5.7.2
- Element Plus 2.9.1
- Vite 6.0.5
- Axios 1.7.9

## 常见问题

### Q: 前端无法连接后端？
A: 确保后端服务已启动在 8000 端口，检查 CORS 配置。

### Q: 上传文件失败？
A: 检查文件格式是否为 CSV/Excel，大小不超过 100MB。

### Q: 分析一直处于"处理中"？
A: 检查后端日志，可能是数据格式问题或算法执行错误。

## 演示准备

为了 10 分钟的课程演示，建议：

1. **准备好示例数据**：使用 `tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv`
2. **提前创建一个项目**：演示时可直接查看结果
3. **熟悉操作流程**：新建项目 → 上传数据 → 查看分析 → 导出报告
4. **准备讲解要点**：
   - 项目架构（前后端分离）
   - Apriori 算法原理
   - 参数选择理由（支持度、置信度）
   - 实际应用场景

## 联系支持

如有问题，请查看：
- API 文档：http://localhost:8000/api/docs
- 后端日志：查看终端输出
- 前端控制台：浏览器开发者工具
