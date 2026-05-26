# MarketMind

MarketMind 是一个面向零售/超市场景的 AI 营销系统，采用 **Vue 3 + FastAPI** 的前后端分离架构，聚焦于项目化的数据分析与智能营销决策。

## 功能概览

- Retail Analysis V2：创建分析项目、上传 CSV、跟踪分析状态
- 购物篮/高效用组合分析：FP-Growth、HUIM 与营销策略建议
- 行为推荐：基于分析结果的个性化推荐能力
- AI 文本建议：基于 LLM 的客户营销建议与商品洞察文本
- 客户分群、营销洞察、促销因果分析
- 数据处理链路：`regularization -> analysis2` 通用分析链路已完整实现并接入后端 runtime，与 Retail V2 并存

## 技术栈

- 后端：FastAPI、Uvicorn、Pydantic、pandas、scikit-learn、mlxtend、httpx
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

## 当前数据集要求

当前后端 `/api/analysis` runtime 只支持 CSV。Retail V2 smoke fixture 位于：

```text
tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv
```

当前 Retail V2 raw CSV 字段契约定义在 `backend/providers/dtos.py` 的
`RETAIL_RAW_SALES_COLUMNS`。

通用数据处理链路已实现：

```text
原始数据上传 -> regularization 正则化 -> analysis2 通用分析 -> 结果产物
```

相关代码位于 `backend/abilities/regularization/`、`backend/abilities/universal_analysis/`、`backend/business/pipelines/` 和 `backend/business/flows/`。归档源材料仍保留在 `analysis/data-processing-pipeline/` 作为参考。

## 目录结构

```
MarketMind/
├── backend/              # FastAPI 后端
├── frontend/             # Vue 3 前端
├── scripts/              # 一键启动脚本（sh/bat）
├── analysis/             # 离线分析蓝本、data-processing pipeline 归档
├── outputs/              # 图表/报告输出
├── data/                 # 项目数据存储
├── docs/                 # 文档（架构/指南/规划）
├── app.py                # Streamlit 单机版入口（可选）
└── pyproject.toml
```

## 相关文档

- 架构说明：`docs/ARCHITECTURE.md`
- 使用指南：`docs/USAGE_GUIDE.md`
- 快速开始：`docs/QUICKSTART.md`
- 数据处理链路方案：`docs/architecture/data-processing-pipeline-integration-design.md`

## 其他入口（可选）

如果需要独立的 Streamlit 版本：
```bash
uv run streamlit run app.py
```

## License

MIT License. See `LICENSE`.
