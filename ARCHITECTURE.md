# MarketMind 系统架构文档

> **Vue3 + FastAPI 前后端分离架构**

---

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户浏览器                               │
│                  http://localhost:5173                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP/WebSocket
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  前端层 (Vue3 + Vite)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  关联规则│  │  销售预测│  │  客户聚类│  │  语音播报│   │
│  │  页面    │  │  页面    │  │  页面    │  │  页面    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│         │             │             │             │          │
│         └─────────────┴─────────────┴─────────────┘          │
│                       │                                      │
│                  ┌────▼────┐                                 │
│                  │  Axios  │                                 │
│                  │  Client │                                 │
│                  └────┬────┘                                 │
└────────────────────────┼──────────────────────────────────────┘
                         │
                         │ REST API (JSON)
                         │
┌────────────────────────▼──────────────────────────────────────┐
│                 后端层 (FastAPI)                               │
│             http://localhost:8000/api                         │
│                                                               │
│  ┌────────────────────── API 路由 ─────────────────────────┐ │
│  │  /association  /prediction  /clustering  /voice         │ │
│  └──────────────────────┬───────────────────────────────────┘ │
│                         │                                     │
│  ┌────────────────────── 服务层 ──────────────────────────┐  │
│  │  AssociationService  PredictionService                  │  │
│  │  ClusteringService   VoiceService                       │  │
│  └──────────────────────┬───────────────────────────────────┘ │
│                         │                                     │
│  ┌────────────────────── 数据层 ──────────────────────────┐  │
│  │  Pandas  NumPy  Scikit-learn  MLxtend  Edge-TTS        │  │
│  └──────────────────────┬───────────────────────────────────┘ │
└────────────────────────┼──────────────────────────────────────┘
                         │
                         ↓
          ┌──────────────────────────────┐
          │       数据存储                │
          │  - dataset.csv (订单数据)    │
          │  - outputs/ (图表、报告)     │
          └──────────────────────────────┘
```

---

## 📁 项目目录结构

```
MarketMind/
├── backend/                    # FastAPI 后端
│   ├── api/                   # API 路由层
│   │   ├── association.py     # 关联规则 API
│   │   ├── prediction.py      # 销售预测 API
│   │   ├── clustering.py      # 客户聚类 API
│   │   └── voice.py           # 语音播报 API
│   ├── core/                  # 核心配置
│   │   └── config.py          # 应用配置
│   ├── models/                # 数据模型
│   │   └── schemas.py         # Pydantic 模型
│   ├── services/              # 业务逻辑层
│   │   ├── association_service.py
│   │   ├── prediction_service.py
│   │   ├── clustering_service.py
│   │   └── voice_service.py
│   ├── utils/                 # 工具函数
│   └── main.py                # FastAPI 应用入口
│
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── api/               # API 调用封装
│   │   ├── components/        # Vue 组件
│   │   ├── views/             # 页面视图
│   │   ├── router/            # 路由配置
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── assets/            # 静态资源
│   │   └── main.ts            # 应用入口
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── analysis/                   # 原始分析代码（参考）
│   ├── dataset.csv            # 数据集
│   ├── marketing_modeling.py  # 原始分析脚本
│   └── *.png                  # 生成的图表
│
├── outputs/                    # API 输出目录
│   ├── charts/                # 图表
│   ├── reports/               # 报告
│   └── audio/                 # 语音文件
│
├── pyproject.toml             # Python 项目配置
├── uv.lock                    # Python 依赖锁定
├── README.md                  # 项目说明
├── ARCHITECTURE.md            # 本文档
├── PROJECT_PLAN.md            # 项目规划
└── QUICKSTART.md              # 快速开始
```

---

## 🔧 技术栈详解

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.13.9 | 编程语言 |
| **FastAPI** | 0.123+ | Web 框架 |
| **Uvicorn** | 0.38+ | ASGI 服务器 |
| **Pydantic** | 2.12+ | 数据验证 |
| **pandas** | 2.3+ | 数据处理 |
| **scikit-learn** | 1.7+ | 机器学习 |
| **mlxtend** | 0.23+ | 关联规则 |
| **matplotlib** | 3.10+ | 可视化 |
| **edge-tts** | 7.2+ | 语音合成 |

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue 3** | 3.x | 前端框架 |
| **Vite** | 5.x | 构建工具 |
| **TypeScript** | 5.x | 类型安全 |
| **Vue Router** | 4.x | 路由管理 |
| **Pinia** | 2.x | 状态管理 |
| **Element Plus** | latest | UI 组件库 |
| **ECharts** | 5.x | 数据可视化 |
| **Axios** | 1.x | HTTP 客户端 |

---

## 🔌 API 接口设计

### 基础信息

- **Base URL**: `http://localhost:8000/api`
- **数据格式**: JSON
- **认证方式**: 暂无（后续可添加 JWT）

### API 端点

#### 1. 关联规则分析

```http
POST /api/association/analyze
Content-Type: application/json

{
  "min_support": 0.02,
  "min_confidence": 0.3,
  "min_lift": 1.0,
  "top_n": 10
}

Response:
{
  "success": true,
  "message": "关联规则分析完成",
  "data": {
    "total_orders": 2088,
    "frequent_itemsets": 307,
    "total_rules": 1170
  },
  "rules": [
    {
      "antecedents": ["纸张", "系固件"],
      "consequent": "椅子",
      "support": 0.0312,
      "confidence": 0.4779,
      "lift": 1.52,
      "strategy": "购买纸张, 系固件的顾客有47.8%概率购买椅子..."
    }
  ],
  "charts": {
    "scatter": "/outputs/charts/association_scatter.png"
  }
}
```

#### 2. 销售预测

```http
POST /api/prediction/forecast
Content-Type: application/json

{
  "forecast_weeks": 13,
  "model_type": "ridge"
}

Response:
{
  "success": true,
  "message": "销售预测完成",
  "forecasts": [
    {
      "week": 1,
      "date": "2024-12-09",
      "sales": 45500,
      "profit": 3500,
      "profit_rate": 0.077
    }
  ],
  "model_performance": {
    "sales_r2": 0.9061,
    "profit_r2": 0.9212
  }
}
```

#### 3. 客户聚类

```http
POST /api/clustering/analyze
Content-Type: application/json

{
  "n_clusters": 4,
  "method": "kmeans"
}

Response:
{
  "success": true,
  "clusters": [
    {
      "cluster_id": 0,
      "name": "高价值活跃客户",
      "customer_count": 258,
      "avg_recency": 107,
      "avg_frequency": 8.34,
      "avg_monetary": 35969,
      "marketing_strategy": "VIP专属优惠..."
    }
  ]
}
```

#### 4. 语音播报

```http
POST /api/voice/generate
Content-Type: application/json

{
  "text": null,  # 自动生成
  "voice": "zh-CN-YunxiNeural",
  "include_modules": ["association", "prediction", "clustering"]
}

Response:
{
  "success": true,
  "text": "超市AI营销系统分析报告...",
  "audio_url": "/outputs/audio/report_20241204.mp3",
  "duration": 30.5
}
```

---

## 🚀 开发流程

### 1. 启动后端（FastAPI）

```bash
# 方式1: 使用 uv run
cd MarketMind
uv run python -m backend.main

# 方式2: 使用 uvicorn 直接运行
uv run uvicorn backend.main:app --reload --port 8000

# 访问 API 文档
open http://localhost:8000/api/docs
```

### 2. 启动前端（Vue3）

```bash
# 首次运行需要初始化
cd frontend
chmod +x init-vue.sh
./init-vue.sh

# 开发运行
npm run dev

# 访问前端
open http://localhost:5173
```

### 3. 同时运行前后端

**终端1 - 后端:**
```bash
uv run uvicorn backend.main:app --reload
```

**终端2 - 前端:**
```bash
cd frontend && npm run dev
```

---

## 🔐 CORS 配置

后端 CORS 已配置允许以下源：
- `http://localhost:3000`
- `http://localhost:5173` (Vite 默认)
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

如需添加其他源，修改 `backend/core/config.py`:

```python
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://your-domain.com"  # 生产环境域名
]
```

---

## 📊 数据流

### 关联规则分析流程

```
用户点击"开始分析"
    ↓
前端发送POST请求到 /api/association/analyze
    ↓
后端 association.py 路由接收请求
    ↓
调用 AssociationService.analyze()
    ↓
1. 加载 dataset.csv
2. 构建购物篮数据
3. Apriori 算法挖掘频繁项集
4. 生成关联规则
5. 筛选 Top N 规则
6. 生成可视化图表（可选）
    ↓
返回 JSON 响应
    ↓
前端接收数据并渲染
```

---

## 🎨 前端页面设计

### 页面结构

```
┌─────────────────────────────────────────┐
│          顶部导航栏 (NavBar)             │
│  Logo | 首页 | 关联规则 | 预测 | 聚类   │
└─────────────────────────────────────────┘
┌──────────┬──────────────────────────────┐
│          │                              │
│  侧边栏  │       主内容区                │
│          │                              │
│  功能导航│     数据展示 + 图表           │
│          │                              │
│  参数配置│                              │
│          │                              │
└──────────┴──────────────────────────────┘
```

### 主要页面

1. **首页 (Home.vue)**
   - 系统介绍
   - 快速开始卡片
   - 数据概览

2. **关联规则页面 (Association.vue)**
   - 参数配置表单
   - Top N 规则表格
   - 支持度-置信度散点图
   - 提升度条形图

3. **销售预测页面 (Prediction.vue)**
   - 预测参数设置
   - 历史趋势图
   - 未来预测曲线
   - 模型性能指标

4. **客户聚类页面 (Clustering.vue)**
   - 聚类参数配置
   - 客户分群表格
   - RFM 对比图
   - 分布散点图

5. **语音播报页面 (Voice.vue)**
   - 文本预览
   - 语音生成
   - 音频播放器

---

## 🧪 测试策略

### 后端测试

```bash
# 单元测试
uv run pytest tests/

# API 测试
curl -X POST http://localhost:8000/api/association/analyze \
  -H "Content-Type: application/json" \
  -d '{"min_support": 0.02}'
```

### 前端测试

```bash
# 单元测试
npm run test

# E2E 测试
npm run test:e2e
```

---

## 📦 部署方案

### 开发环境
- 后端: `uvicorn --reload`
- 前端: `npm run dev`

### 生产环境

**选项1: 独立部署**
- 后端: Docker + Gunicorn + Nginx
- 前端: Vercel / Netlify

**选项2: 集成部署**
- 前端构建后放到 `backend/static/`
- FastAPI 同时提供 API 和静态文件服务

**Docker 部署**

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync
COPY backend ./backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
```

---

## 🔄 团队协作

### Git 分支策略

```
main (生产环境)
  ├── dev (开发环境)
  │   ├── feature/association (功能分支)
  │   ├── feature/prediction
  │   ├── feature/clustering
  │   └── feature/voice
```

### 工作流程

1. **后端开发** (2人)
   - 人员A: 关联规则 + 预测模块
   - 人员B: 聚类 + 语音模块

2. **前端开发** (1人)
   - Vue3 页面开发
   - API 集成

3. **测试+文档** (1人)
   - API 测试
   - 文档编写

4. **组长** (1人)
   - 代码集成
   - 项目协调

---

## 📖 相关文档

- [快速开始](QUICKSTART.md)
- [项目规划](PROJECT_PLAN.md)
- [后端 API 文档](http://localhost:8000/api/docs)
- [前端开发指南](frontend/README.md)

---

**更新时间**: 2024-12-04
**架构版本**: 1.0.0
