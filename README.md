# MarketMind

MarketMind 是一个面向零售/超市场景的 AI 营销系统，采用 **Vue 3 + FastAPI** 的前后端分离架构，聚焦于项目化的数据分析与智能营销决策。

## 功能概览

- 项目管理：创建项目、上传数据、跟踪分析状态
- 关联规则分析：Apriori 购物篮分析与营销策略建议
- 行为推荐：基于分析结果的推荐能力
- AI 语音播报：分析报告生成与语音合成
- 销售预测、客户聚类（部分功能仍在开发中）

## 技术栈

- 后端：FastAPI、Uvicorn、Pydantic、pandas、scikit-learn、mlxtend、edge-tts
- 前端：Vue 3、Vite、TypeScript、Pinia、Vue Router、Element Plus、ECharts、Axios

## 环境要求

- Python 3.13.x（项目约束：`>=3.13,<3.14`，建议 3.13.9）
- [uv](https://github.com/astral-sh/uv) 包管理器
- Node.js 18+ 与 npm

## 快速启动（推荐脚本）

macOS / Linux:
```bash
bash scripts/start-project.sh
```

Windows:
```bat
scripts\start-project.bat
```

脚本会自动安装依赖、创建必要目录并启动前后端服务：
- 前端：`http://localhost:5173`
- 后端 API：`http://localhost:8000/api`
- API 文档：`http://localhost:8000/api/docs`

## 手动启动（分步）

### 1) 后端
```bash
uv sync
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) 前端
```bash
cd frontend
npm install
npm run dev
```

前端默认使用 `.env.development` 中的配置（脚本会自动生成）：
```
VITE_API_BASE_URL=http://localhost:8000/api
VITE_API_TIMEOUT=30000
```

## 数据集要求

支持 CSV / Excel（`.csv` / `.xlsx` / `.xls`），必要字段示例：
```
订单 ID, 订单日期, 客户ID, 产品ID, 子类别, 销售额, 折扣, 利润
```

项目内置示例数据：`analysis/dataset.csv`

## 目录结构

```
MarketMind/
├── backend/              # FastAPI 后端
├── frontend/             # Vue 3 前端
├── scripts/              # 一键启动脚本（sh/bat）
├── analysis/             # 离线分析与样例数据
├── outputs/              # 图表/报告/语音输出
├── data/                 # 项目数据存储
├── docs/                 # 文档（架构/指南/规划）
├── app.py                # Streamlit 单机版入口（可选）
└── pyproject.toml
```

## 相关文档

- 架构说明：`docs/ARCHITECTURE.md`
- 使用指南：`docs/USAGE_GUIDE.md`
- 快速开始：`docs/QUICKSTART.md`

## 其他入口（可选）

如果需要独立的 Streamlit 版本：
```bash
uv run streamlit run app.py
```
