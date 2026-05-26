# MarketMind Frontend

Vue 3 + Vite frontend for Retail Analysis V2, Data Processing, recommendations, and customer text suggestions.

## Stack

- Vue 3.5
- Vite 6
- TypeScript 5.7
- Vue Router
- Pinia
- Axios
- Element Plus
- ECharts / vue-echarts

## Development

```bash
cd frontend
npm install
npm run dev
```

Build:

```bash
npm run build
```

The dev server runs at `http://localhost:5173`.

## API Boundary

Pages call the backend through `frontend/src/api/`:

```text
src/api/
  client.ts            # axios instance, timeout, envelope unwrap
  errors.ts            # normalized API errors
  types.ts             # shared API DTOs and status helpers
  health.ts            # GET /api/health/
  retail.ts            # Retail V2 endpoints
  data-processing.ts   # Data Processing endpoints
  suggestions.ts       # POST /api/analysis/customer-suggestions
  index.ts             # barrel exports
```

Do not add page-local raw axios calls for MarketMind business endpoints. Do not reintroduce retired routes `/api/projects`, `/api/recommend`, or `/api/association`.

## Routes

| Route | Page | Purpose |
| --- | --- | --- |
| `/` | `Home.vue` | Home entry. |
| `/projects` | `ProjectList.vue` | Retail V2 project list. |
| `/projects/new` | `ProjectCreate.vue` | Retail V2 create/upload/run. |
| `/projects/:id` | `ProjectDetail.vue` | Retail V2 details, stages, artifacts, recommendations. |
| `/projects/:id/recommend` | `ProductRecommend.vue` | Recommendation exploration and product insight text. |
| `/projects/:id/customer/:customerId` | `CustomerAnalysis.vue` | Customer detail and suggestion text. |
| `/data-processing` | `DataProcessing.vue` | Create/upload/regularize/run Data Processing jobs. |
| `/data-processing/jobs/:jobId` | `DataProcessing.vue` | Read an existing Data Processing job with `project_id` query. |
| `/settings` | `Settings.vue` | Local LLM config passed to backend suggestion endpoint. |

## Environment

`frontend/vite.config.ts` proxies `/api` and `/outputs` to `http://localhost:8000` in local development.

Optional Vite variables:

```env
VITE_API_BASE_URL=
VITE_API_TIMEOUT=30000
```

Set `VITE_API_BASE_URL` when the frontend and API are not served from the same origin or Vite proxy is unavailable.

## LLM Rule

Business pages call `POST /api/analysis/customer-suggestions`. They should not call third-party `/chat/completions` or `/models` directly from the browser.

## Verification

From the repository root:

```bash
make build
make check
```

From `frontend/` only:

```bash
npm run build
```
