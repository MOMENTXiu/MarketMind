# MarketMind 使用指南

MarketMind 当前提供两条前端工作流：Retail Analysis V2 和 Data Processing。两条链路都通过后端 `/api/analysis` 接口运行。

## 启动服务

后端：

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

访问：

- 前端：`http://localhost:5173`
- API docs：`http://localhost:8000/api/docs`

## Retail Analysis V2

Retail V2 面向固定中文列零售销售 CSV。

### 入口

```text
/projects
/projects/new
/projects/{project_id}
/projects/{project_id}/recommend
/projects/{project_id}/customer/{customer_id}
```

### 流程

1. 打开“我的项目”。
2. 新建项目，填写名称和描述。
3. 上传 Retail V2 CSV。
4. 前端调用 `POST /api/analysis/projects/{project_id}/dataset` 完成数据准备。
5. 前端调用 `POST /api/analysis/projects/{project_id}/run` 启动分析。
6. 页面轮询 `GET /api/analysis/projects/{project_id}`，直到 `completed` 或 `failed`。
7. 项目详情页展示 summary、quality、stage status、artifact refs、推荐结果和营销洞察。

### 数据要求

Retail V2 当前只接受 CSV。字段以 `backend/providers/dtos.py` 的 `RETAIL_RAW_SALES_COLUMNS` 为准：

```text
顾客编号,大类编码,大类名称,中类编码,中类名称,小类编码,小类名称,销售日期,销售月份,商品编码,规格型号,商品类型,单位,销售数量,销售金额,商品单价,是否促销
```

本地冒烟数据：

```text
tests/fixtures/analysis_v2/retail_sales_raw_gbk.csv
```

## Data Processing

Data Processing 面向通用 CSV/Excel，适合列名不固定的数据。链路为：

```text
raw dataset upload -> regularization -> analysis2 universal analysis -> output refs
```

### 入口

```text
/data-processing
/data-processing/jobs/{job_id}?project_id={project_id}
```

### 流程

1. 打开“数据处理”。
2. 填写 `project_id` 和 Job 名称。
3. 上传 `.csv`、`.xls` 或 `.xlsx`。
4. 执行标准化。
5. 查看 quality、capability、stages、skipped reasons 和 sidecars。
6. 若状态为 `needs_review`，先查看 Schema Mapping、Quality Report、Capability；当前没有 approval endpoint，运行按钮保持禁用。
7. 若标准化通过，运行分析。
8. 页面轮询 Job 状态，完成后展示 outputs 与 sidecar JSON。

### 状态

| 状态 | 含义 |
| --- | --- |
| `queued` | 已创建或等待执行。 |
| `processing` | 后端正在执行分析。 |
| `completed` | 当前阶段完成。 |
| `failed` | 执行失败，查看 `error`。 |
| `needs_review` | core 字段映射需要复核，不能继续 run。 |

optional/marketing 字段的 fuzzy mapping 不阻断完整分析。没有共购结构时，association 可以 `skipped`，Job 仍可 `completed`。

## AI 文本建议

客户详情页和商品关联页通过后端 `POST /api/analysis/customer-suggestions` 获取文本建议。浏览器不直接请求第三方 `/chat/completions` 或 `/models`。

设置页保存的 LLM 配置存在浏览器本地，用于随请求传给后端建议接口。生产环境需要服务端侧密钥管理和鉴权后再开放真实模型配置。

## 服务状态

导航栏服务状态组件调用 `GET /api/health/`。后端离线时显示不可用；组件卸载时会清理轮询 timer。

## 输出和产物

前端只展示后端返回的 ref/url，不拼接本地绝对路径。

| 链路 | 产物入口 |
| --- | --- |
| Retail V2 | `GET /api/analysis/projects/{project_id}/artifacts` |
| Data Processing | `GET /api/analysis/jobs/{job_id}/outputs?project_id=...` |
| Data Processing sidecars | `GET /api/analysis/jobs/{job_id}/sidecars/{sidecar_id}?project_id=...` |

## 常见问题

### 前端无法连接后端

确认后端在 `8000` 端口运行。开发环境默认由 Vite proxy 转发 `/api`；跨域部署时设置 `VITE_API_BASE_URL`。

### Retail 上传失败

检查文件是否为 CSV，并确认列名符合 `RETAIL_RAW_SALES_COLUMNS`。

### Data Processing 无法继续运行

若 Job 状态为 `needs_review`，说明 core 字段需要复核。当前没有 approval endpoint，前端会阻止 run。

### 分析一直 processing

当前后台任务使用 FastAPI in-process background tasks。Redis Queue 落地前，用单 worker 运行后端，避免多进程状态不可见。

## 质量检查

```bash
make check
make hooks
```

当前基线为 `188 passed, 5 skipped`，前端 `npm run build` 通过。pandas/numpy/pydantic warnings 属于已知非阻塞输出。
