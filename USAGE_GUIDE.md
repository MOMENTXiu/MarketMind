# MarketMind 使用指南

## 系统架构说明

MarketMind 已重构为**项目管理模式**，采用 Vue3 + FastAPI 前后端分离架构。

### 核心功能

1. **项目管理**：创建、管理和分析多个营销数据项目
2. **关联规则分析**：基于 Apriori 算法的购物篮分析
3. **销售预测**：时间序列预测模型（开发中）
4. **客户聚类**：RFM 模型 + K-Means 聚类（开发中）
5. **语音播报**：AI 自动生成分析报告并语音播报

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

#### 3. 销售预测（开发中）
- 预测周数设置
- 未来销售额和利润预测图表

#### 4. 客户聚类（开发中）
- RFM 模型分析
- K-Means 聚类结果
- 客户分群特征

#### 5. 语音播报
- 🔊 播放按钮
- 音频播放器
- 自动生成的分析报告播报

## 项目状态说明

- **待处理**：项目已创建，但数据集未上传
- **处理中**：正在执行数据分析（页面会自动刷新）
- **已完成**：分析完成，可查看结果
- **失败**：分析过程中出现错误

## 数据集要求

### 文件格式
- CSV 文件（推荐）
- Excel 文件（.xlsx, .xls）

### 必需字段
```
订单 ID, 订单日期, 客户ID, 产品ID, 子类别, 销售额, 折扣, 利润
```

### 示例数据
可使用项目自带的示例数据集：
```bash
analysis/dataset.csv
```

## API 接口说明

### 项目管理
- `POST /api/projects/` - 创建项目
- `GET /api/projects/` - 获取项目列表
- `GET /api/projects/{id}` - 获取项目详情
- `PUT /api/projects/{id}` - 更新项目
- `DELETE /api/projects/{id}` - 删除项目

### 文件上传
- `POST /api/projects/{id}/upload` - 上传数据集并开始分析

### 分析操作
- `POST /api/projects/{id}/reanalyze` - 重新分析

### 结果下载
- `GET /api/projects/{id}/download/report` - 下载分析报告
- `GET /api/projects/{id}/audio` - 获取语音文件

## 目录结构

```
MarketMind/
├── backend/                 # 后端 FastAPI 服务
│   ├── api/                # API 路由
│   │   ├── projects.py    # 项目管理 API
│   │   ├── association.py # 关联规则 API
│   │   ├── prediction.py  # 销售预测 API
│   │   ├── clustering.py  # 客户聚类 API
│   │   └── voice.py       # 语音播报 API
│   ├── core/              # 核心模块
│   │   ├── config.py      # 配置管理
│   │   └── storage.py     # 项目存储管理
│   ├── models/            # 数据模型
│   │   ├── project.py     # 项目模型
│   │   └── schemas.py     # API schemas
│   ├── services/          # 业务服务
│   │   ├── analysis_service.py    # 分析服务
│   │   ├── association_service.py # 关联规则服务
│   │   └── tts_service.py         # TTS 语音服务
│   └── main.py            # 应用入口
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
│           ├── dataset.csv    # 数据集
│           └── outputs/       # 输出文件
│               ├── charts/    # 图表
│               ├── reports/   # 报告
│               └── audio/     # 语音文件
└── analysis/              # 原始分析代码（参考）
```

## 开发状态

### ✅ 已完成
- 项目管理系统
- 关联规则分析（Apriori 算法）
- 语音合成（Edge-TTS）
- 前后端架构重构
- 多步表单创建流程
- 项目详情页面

### 🚧 开发中
- 销售预测模块（迁移中）
- 客户聚类模块（迁移中）
- 数据可视化图表集成

## 技术栈

### 后端
- Python 3.13
- FastAPI 0.123.5
- Pydantic 2.12.5
- pandas, numpy, scikit-learn
- mlxtend (Apriori)
- edge-tts (语音合成)

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

### Q: 语音文件无法播放？
A: 确保 Edge-TTS 已正确安装，检查网络连接。

## 演示准备

为了 10 分钟的课程演示，建议：

1. **准备好示例数据**：使用 `analysis/dataset.csv`
2. **提前创建一个项目**：演示时可直接查看结果
3. **熟悉操作流程**：新建项目 → 上传数据 → 查看分析 → 播放语音
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
