# 超市AI营销系统 (MarketMind)

> **Vue3 + FastAPI 前后端分离架构** | 基于机器学习的智能营销决策支持系统

## 🎯 项目简介

MarketMind是一个现代化的AI营销分析系统，采用前后端分离架构，为超市零售业提供数据驱动的营销决策支持。

### 核心功能

- 📊 **关联规则分析**: 基于Apriori算法的购物篮分析，制定商品组合促销策略
- 📈 **销售预测**: 时间序列预测模型，预测未来销售额和利润
- 👥 **客户聚类**: RFM模型+K-Means聚类，实现精准营销
- 🔊 **语音播报**: AI自动生成并播报分析报告

### 技术架构

```
┌──────────────┐      HTTP/JSON      ┌──────────────┐
│  Vue3 前端    │ ←────────────────→ │ FastAPI 后端 │
│  (Port 5173) │                    │  (Port 8000) │
└──────────────┘                    └──────────────┘
```

## 🚀 快速开始

### 环境要求

- **后端**: Python 3.13+, uv
- **前端**: Node.js 18+, npm/pnpm

### 1. 后端启动（FastAPI）

```bash
# 安装Python依赖
uv sync

# 启动后端API服务
./start-backend.sh
# 或手动启动
uv run uvicorn backend.main:app --reload

# 访问 API 文档
open http://localhost:8000/api/docs
```

### 2. 前端启动（Vue3）

```bash
# 初始化Vue3项目（首次运行）
cd frontend
./init-vue.sh

# 启动开发服务器
npm run dev

# 访问前端页面
open http://localhost:5173
```

### 3. 测试 API

```bash
# 健康检查
curl http://localhost:8000/api/health

# 关联规则分析
curl -X POST http://localhost:8000/api/association/analyze \
  -H "Content-Type: application/json" \
  -d '{"min_support": 0.02, "top_n": 10}'
```

## 📦 技术栈

### 后端
- **Python 3.13.9** - 编程语言
- **FastAPI** - 现代Web框架
- **Uvicorn** - ASGI服务器
- **Pydantic** - 数据验证
- **pandas/numpy** - 数据处理
- **scikit-learn** - 机器学习
- **mlxtend** - 关联规则挖掘
- **edge-tts** - 语音合成

### 前端
- **Vue 3** - 渐进式框架
- **Vite** - 构建工具
- **TypeScript** - 类型安全
- **Element Plus** - UI组件库
- **ECharts** - 数据可视化
- **Axios** - HTTP客户端
- **Pinia** - 状态管理
- **Vue Router** - 路由管理

## 📁 项目结构

```
MarketMind/
├── backend/                    # FastAPI 后端
│   ├── api/                   # API 路由
│   │   ├── association.py     # 关联规则API
│   │   ├── prediction.py      # 预测API
│   │   ├── clustering.py      # 聚类API
│   │   └── voice.py           # 语音API
│   ├── core/                  # 核心配置
│   ├── models/                # 数据模型
│   ├── services/              # 业务逻辑
│   └── main.py                # FastAPI入口
│
├── frontend/                   # Vue3 前端
│   ├── src/                   # 源代码
│   │   ├── api/              # API调用
│   │   ├── views/            # 页面
│   │   ├── components/       # 组件
│   │   └── router/           # 路由
│   └── package.json
│
├── analysis/                   # 原始分析代码
│   ├── dataset.csv            # 数据集
│   └── marketing_modeling.py  # 分析脚本
│
├── outputs/                    # API输出
│   ├── charts/                # 图表
│   ├── reports/               # 报告
│   └── audio/                 # 语音
│
├── pyproject.toml             # Python项目配置
├── uv.lock                    # 依赖锁定
├── ARCHITECTURE.md            # 架构文档
├── PROJECT_PLAN.md            # 项目规划
└── README.md                  # 本文档
```

## 🔌 API 接口

### Base URL: `http://localhost:8000/api`

| 端点 | 方法 | 功能 |
|------|------|------|
| `/association/analyze` | POST | 关联规则分析 |
| `/prediction/forecast` | POST | 销售预测 |
| `/clustering/analyze` | POST | 客户聚类 |
| `/voice/generate` | POST | 语音播报 |
| `/health` | GET | 健康检查 |

完整API文档: http://localhost:8000/api/docs

## 📚 文档

- [系统架构](ARCHITECTURE.md) - 详细架构设计
- [项目规划](PROJECT_PLAN.md) - 开发计划与分工
- [快速开始](QUICKSTART.md) - 详细使用指南
- [前端开发](frontend/README.md) - Vue3开发文档

## 🎓 团队协作

### 推荐分工（6-7人）

| 角色 | 人数 | 职责 |
|------|------|------|
| 组长 | 1 | 整体协调、代码集成 |
| 后端开发 | 2 | FastAPI + 算法实现 |
| 前端开发 | 1 | Vue3 界面开发 |
| 测试+文档 | 1-2 | 测试、文档、演示PPT |

### Git工作流

```bash
# 克隆项目
git clone <repo-url>
cd MarketMind

# 后端开发
git checkout -b feature/backend-xxx
# 开发...
git commit && git push

# 前端开发
git checkout -b feature/frontend-xxx
# 开发...
git commit && git push
```

## 🚀 部署

### 开发环境
```bash
# 后端
./start-backend.sh

# 前端
cd frontend && npm run dev
```

### 生产环境
```bash
# 后端
uv run gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker

# 前端
cd frontend
npm run build
# 部署 dist/ 目录到 Nginx/Vercel/Netlify
```

### Docker部署
```bash
docker-compose up -d
```

## 📊 演示效果

- API 文档: http://localhost:8000/api/docs
- 前端页面: http://localhost:5173
- 数据可视化: 17张分析图表
- 语音播报: AI自动生成

## 👥 贡献者

MarketMind Team

## 📄 许可证

MIT License

---

**当前版本**: 1.0.0
**更新日期**: 2024-12-04
**架构**: Vue3 + FastAPI 前后端分离
