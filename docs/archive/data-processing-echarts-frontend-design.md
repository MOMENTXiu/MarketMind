# Data Processing ECharts Frontend Design

Status: active design, 2026-05-28.

## Problem Statement

The data-processing chain now runs end to end, but the project detail UI still
shows completed outputs as raw artifact cards:

```text
raw_upload
normalized_dataset
sidecar:quality_report
json:universal_overview.json
json:universal_profile_segments.json
json:universal_recommendation.json
json:universal_promotion.json
json:universal_summary.json
model:segmentation:current
```

This is expected from the current frontend implementation, but it is not the
expected product experience. `frontend/src/views/ProjectDetail.vue` renders
`visibleArtifactRefs` as a grid of links for every project. Retail projects get
one ECharts forecast block, but data-processing projects do not load JSON
artifact payloads or convert those payloads into visual dashboards.

`frontend/src/views/DataProcessing.vue` has the same gap: it displays quality,
capability, output refs, and sidecar JSON, but it does not render analysis
results as charts.

## Current Frontend Findings

| File | Current behavior | Gap |
| --- | --- | --- |
| `frontend/src/views/ProjectDetail.vue` | Imports ECharts and renders `forecastOption` only for Retail prediction data. | Data-processing projects fall through to generic artifact cards. |
| `frontend/src/views/ProjectDetail.vue` | `loadDetailPayloads()` fetches only Retail CSV artifact names. | It never fetches `json:universal_*.json` payloads. |
| `frontend/src/views/DataProcessing.vue` | Calls job/status/output/sidecar APIs and pretty-prints sidecars. | It never calls artifact payload endpoints for universal JSON outputs. |
| `frontend/src/api/retail.ts` | Already exposes `getRetailArtifactPayload(projectId, artifactId)`. | The wrapper name is Retail-specific, but the backend route also works for data-processing JSON refs through `/api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload`. |
| `frontend/package.json` | Already includes `echarts` and `vue-echarts`. | No new chart library is needed. |

## Backend Result Shape

Runtime data-processing outputs are saved as project-scoped analysis artifacts
through `AnalysisArtifactProvider.save_json`. The JSON payloads are available
through the existing payload endpoint:

```text
GET /api/analysis/projects/{project_id}/artifacts/{artifact_id}/payload
```

For example:

```text
GET /api/analysis/projects/{project_id}/artifacts/json:universal_overview.json/payload
```

The API returns an envelope whose data contains:

- `payload_type: "json"`
- `artifact`
- `payload`

The backend currently emits these visualizable payloads:

| Artifact id | Source ability | Useful fields |
| --- | --- | --- |
| `json:universal_summary.json` | `build_universal_summary` | `基础销售统计`, `顾客画像`, `关联规则`, `个性化推荐`, `促销分析` |
| `json:universal_overview.json` | `build_overview` | `overview`, `category_sales`, `daily_sales`, `promo_share`, `top_category`, `pareto_top20pct_share` |
| `json:universal_profile_segments.json` | `build_profile_segments` | `n_segments`, `silhouette`, `segment_profiles`, `customer_segments`, `kscan`, `features_used` |
| `json:universal_association.json` | `mine_universal_associations` | `rules`, `huim`, `level`, `avg_basket`, `n_rules`, `avg_lift`, `top_rule` |
| `json:universal_recommendation.json` | `rank_universal_recommendations` | `evaluation`, `reliability`, `best_model`, `fusion_hit`, `best_single_hit`, `fusion_vs_best` |
| `json:universal_promotion.json` | `estimate_universal_promotion_effect` | `naive_diff`, `dml_ate`, `dml_ci`, `dml_significant`, `discount_levels`, `profit_margin`, `total_profit` |

## Archive Visualization Reference

The archived `analysis/` and `analysis/data-processing-pipeline/analysis2/`
directories are reference snapshots, not backend runtime imports. They show the
expected visualization intent:

| Historical output | Historical chart | ECharts target |
| --- | --- | --- |
| `overview_category.csv`, `overview_类目帕累托.png` | Category sales bar + cumulative Pareto line | Bar + line with dual y-axis from `category_sales`. |
| `overview_时间趋势.png` | Daily sales trend and rolling mean | Line chart from `daily_sales`, with optional moving average in frontend. |
| `overview_促销对比.png` | Promotion vs non-promotion sales | Bar/KPI from `promo_share`; richer chart requires backend to emit both promo and non-promo amounts. |
| `segment_kscan.csv` | K scan model comparison | Line chart for `kscan.k` vs `轮廓系数` and optional `DB指数`. |
| `segment_聚类散点.png` | RFM cluster scatter | Scatter from customer-level segment data; current runtime only exposes `user_id` + `分群`, so this needs backend enrichment before it can be reproduced. |
| `segment_雷达画像.png` | Segment radar profile | Radar from numeric columns in `segment_profiles`. |
| `segment_销售贡献.png` | People share vs sales contribution | Grouped bar from `segment_profiles.人数占比` and `销售贡献占比`. |
| `as_规则指标分布.png` | Confidence/lift/support bubble | Scatter from `rules`: x=`置信度`, y=`提升度`, size=`支持度`. |
| `14_Top组合效用.png` | Top bundle utility bar | Horizontal bar from `huim.组合` and `总效用`. |
| `17_推荐命中率对比.png` | Recommendation model comparison | Grouped bar from `evaluation` metrics. |
| `18_CRITIC指标权重.png` | Signal weight bar | Bar from `reliability`; label as reliability unless backend emits actual weights. |
| `mk_促销因果效应.png` | Naive vs DML effect forest | Bar/interval chart from `naive_diff`, `dml_ate`, `dml_ci`. |
| `clv_*`, `ch_*`, `ts_*`, `el_*`, `mc_*` | CLV/churn/time-series/elasticity/Monte Carlo visuals | Out of current universal runtime scope unless those abilities are ported. |

## Target UX

Data-processing project detail should become an analysis dashboard first, with
raw refs as a secondary diagnostics section.

Recommended order:

1. KPI summary: records, users, items, orders, total sales, AOV, return rate,
   promo share, segment count, silhouette, association rule count, best
   recommendation model, DML ATE.
2. Overview charts: category Pareto and daily sales trend.
3. Segment charts: contribution grouped bar, radar profile, k-scan line.
4. Association charts: rule metric bubble and top utility bundles.
5. Recommendation charts: model metric comparison and signal reliability.
6. Promotion charts: naive vs DML effect with CI and discount level response.
7. Diagnostics: quality/capability, sidecars, raw output refs.

The `/data-processing/jobs/:jobId` page can keep its workflow/operator role, but
after completion it should reuse the same chart components or link directly to
the project detail dashboard.

## Frontend Architecture

Add a data-processing artifact read model under the frontend API boundary:

```text
frontend/src/api/analysis-artifacts.ts
frontend/src/api/types.ts
```

Suggested wrapper:

```ts
getAnalysisArtifactPayload(projectId: string, artifactId: string): Promise<AnalysisArtifactPayload>
```

This should replace direct page-local axios usage and can wrap the same backend
endpoint currently used by `getRetailArtifactPayload`.

Add a small chart-building layer instead of embedding all transforms inside
Vue templates:

```text
frontend/src/utils/data-processing-charts.ts
frontend/src/components/data-processing/
  DpKpiStrip.vue
  DpOverviewCharts.vue
  DpSegmentCharts.vue
  DpAssociationCharts.vue
  DpRecommendationCharts.vue
  DpPromotionCharts.vue
```

`ProjectDetail.vue` should orchestrate loading and layout:

```text
if analysis_kind === "data_processing":
  fetch output refs
  find json:universal_*.json refs
  fetch payloads in parallel
  pass payloads to chart components
  show artifact cards only under Diagnostics
else:
  keep Retail dashboard path
```

## Chart Mapping

### Summary KPI Strip

Source:

- `universal_summary.payload`
- fallback to module payloads when summary is missing

Render:

- compact KPI tiles, not cards inside cards
- values formatted with existing `formatValue`
- skipped modules show as subdued tags with their reason where available

### Overview Charts

Source:

- `universal_overview.payload.category_sales`
- `universal_overview.payload.daily_sales`

Render:

- category Pareto: `bar` for top categories, cumulative `line` on second y-axis
- daily sales: `line`, plus frontend-computed 7-day or 30-day moving average
  depending on series length

### Segment Charts

Source:

- `universal_profile_segments.payload.segment_profiles`
- `universal_profile_segments.payload.kscan`

Render:

- contribution grouped bar: `人数占比` vs `销售贡献占比`
- radar: normalize numeric segment profile fields in frontend, exclude ids and
  counts from radar axes
- k-scan: line for `轮廓系数`; optional second series for `DB指数`

Known backend gap:

- current `customer_segments` only contains `user_id` and `分群`, so the
  historical RFM scatter cannot be recreated. To render scatter, backend should
  emit either sampled customer points with x/y features or a chart-ready
  `scatter_points` array.

### Association Charts

Source:

- `universal_association.payload.rules`
- `universal_association.payload.huim`

Render:

- confidence/lift bubble: `置信度` vs `提升度`, symbol size from `支持度`
- top bundle utility: horizontal bar from `总效用`
- table preview for top rules remains useful below the chart

### Recommendation Charts

Source:

- `universal_recommendation.payload.evaluation`
- `universal_recommendation.payload.reliability`

Render:

- grouped bar for `Precision@10`, `Recall@10`, `HitRate@10`, `NDCG@10`,
  `Coverage`
- signal reliability bar for `graph`, `cat`, `pop`

Note:

- historical docs mention CRITIC weights, but runtime payload currently exposes
  reliability, not final fused weights. Label accurately.

### Promotion Charts

Source:

- `universal_promotion.payload.naive_diff`
- `universal_promotion.payload.dml_ate`
- `universal_promotion.payload.dml_ci`
- `universal_promotion.payload.discount_levels`

Render:

- effect comparison: bar for naive vs DML, with CI interval for DML
- discount levels: bar from discount bucket to average amount
- profit KPIs from `profit_margin` and `total_profit` when present

## Backend Gaps To Consider

The first frontend slice can be implemented using current JSON payloads. These
backend improvements are optional but would make the dashboard closer to the
historical `analysis/` figures:

1. Add `promo_sales_by_flag` to `universal_overview` for a true promotion vs
   non-promotion chart.
2. Add `scatter_points` or `profile_sample` to `universal_profile_segments`
   for an RFM/feature scatter.
3. Add recommendation chart-ready source composition if the product wants the
   old `15_推荐来源占比.png` view.
4. Add time-series forecast, CLV, churn, elasticity, and Monte Carlo abilities
   only if those modules are intentionally brought into backend runtime.

## Validation Strategy

- Unit-test chart option builders with representative payload fixtures.
- Frontend build: `cd frontend && npm run build`.
- Browser smoke through the real flow: create project, upload CSV, run
  analysis, open project detail, verify chart sections render without console
  errors.
- API smoke: fetch each `json:universal_*.json/payload` URL and ensure payloads
  are JSON-safe and path-free.
- Full project quality loop before handoff: `make lint`, `make format`,
  `make lint`; run `make check` when implementation touches frontend/runtime
  behavior.

## Rollback

The frontend implementation should be removable without backend migration:

- remove the new chart components and chart utility
- remove the generic artifact payload wrapper if unused
- restore data-processing project detail to artifact cards
- keep backend universal JSON artifacts unchanged
