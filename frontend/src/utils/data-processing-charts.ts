import type { EChartsOption } from 'echarts'

// ─── Type Definitions ───

export interface KpiTile {
  label: string
  value: string
  sub?: string
}

export interface OverviewPayload {
  overview?: Record<string, unknown>
  category_sales?: Array<Record<string, unknown>>
  daily_sales?: Array<Record<string, unknown>>
  promo_share?: Record<string, unknown>
  top_category?: string
  pareto_top20pct_share?: number
}

export interface SegmentProfile {
  分群?: string
  cluster_id?: number | string
  人数占比?: number
  销售贡献占比?: number
  [key: string]: unknown
}

export interface KScanPoint {
  k?: number
  轮廓系数?: number
  'DB指数'?: number
}

export interface SegmentPayload {
  n_segments?: number
  silhouette?: number
  segment_profiles?: SegmentProfile[]
  customer_segments?: Array<Record<string, unknown>>
  kscan?: KScanPoint[]
  features_used?: string[]
}

export interface AssociationRule {
  前项?: string
  后项?: string
  置信度?: number
  提升度?: number
  支持度?: number
  [key: string]: unknown
}

export interface HuimItem {
  组合?: string
  总效用?: number
  [key: string]: unknown
}

export interface AssociationPayload {
  rules?: AssociationRule[]
  huim?: HuimItem[]
  level?: string
  avg_basket?: number
  n_rules?: number
  avg_lift?: number
  top_rule?: AssociationRule
}

export interface EvaluationMetric {
  model?: string
  'Precision@10'?: number
  'Recall@10'?: number
  'HitRate@10'?: number
  NDCG?: number
  'NDCG@10'?: number
  Coverage?: number
  [key: string]: unknown
}

export interface RecommendationPayload {
  evaluation?: EvaluationMetric[]
  reliability?: Record<string, number>
  best_model?: string
  fusion_hit?: number
  best_single_hit?: number
  fusion_vs_best?: number
}

export interface DiscountLevel {
  discount?: string | number
  avg_amount?: number
  count?: number
}

export interface PromotionPayload {
  naive_diff?: number
  dml_ate?: number
  dml_ci?: [number, number] | null
  dml_significant?: boolean
  discount_levels?: DiscountLevel[]
  profit_margin?: number
  total_profit?: number
}

export interface SummaryPayload {
  基础销售统计?: Record<string, unknown>
  顾客画像?: Record<string, unknown>
  关联规则?: Record<string, unknown>
  个性化推荐?: Record<string, unknown>
  促销分析?: Record<string, unknown>
}

// ─── Helpers ───

const toNum = (v: unknown, fallback = 0): number => {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

const fmt = (v: number, digits = 2): string =>
  v.toLocaleString('zh-CN', { maximumFractionDigits: digits })

const fmtPct = (v: number, digits = 1): string =>
  `${(v * 100).toFixed(digits)}%`

// ─── KPI Strip ───

export function buildKpiTiles(summary?: SummaryPayload | null): KpiTile[] {
  if (!summary) return []
  const tiles: KpiTile[] = []
  const stats = summary.基础销售统计 || {}
  if (stats.总记录数 !== undefined) tiles.push({ label: '总记录', value: fmt(toNum(stats.总记录数), 0) })
  if (stats.用户数 !== undefined) tiles.push({ label: '用户数', value: fmt(toNum(stats.用户数), 0) })
  if (stats.商品数 !== undefined) tiles.push({ label: '商品数', value: fmt(toNum(stats.商品数), 0) })
  if (stats.订单数 !== undefined) tiles.push({ label: '订单数', value: fmt(toNum(stats.订单数), 0) })
  if (stats.总销售额 !== undefined) tiles.push({ label: '总销售额', value: `¥${fmt(toNum(stats.总销售额))}` })
  if (stats.客单价 !== undefined) tiles.push({ label: '客单价', value: `¥${fmt(toNum(stats.客单价))}` })
  if (stats.退货率 !== undefined) tiles.push({ label: '退货率', value: fmtPct(toNum(stats.退货率)) })

  const seg = summary.顾客画像 || {}
  if (seg.分群数 !== undefined) tiles.push({ label: '分群数', value: fmt(toNum(seg.分群数), 0) })
  if (seg.轮廓系数 !== undefined) tiles.push({ label: '轮廓系数', value: fmt(toNum(seg.轮廓系数), 3) })

  const assoc = summary.关联规则 || {}
  if (assoc.规则数 !== undefined) tiles.push({ label: '关联规则', value: fmt(toNum(assoc.规则数), 0) })

  const rec = summary.个性化推荐 || {}
  if (rec.最佳模型 !== undefined) tiles.push({ label: '最佳模型', value: String(rec.最佳模型) })

  const promo = summary.促销分析 || {}
  if (promo.DML_ATE !== undefined) tiles.push({ label: 'DML ATE', value: fmt(toNum(promo.DML_ATE), 3) })

  return tiles
}

// ─── Overview: Category Pareto ───

export function buildCategoryParetoOption(
  categorySales?: Array<Record<string, unknown>> | null
): EChartsOption {
  if (!categorySales?.length) return {}
  const sorted = [...categorySales].sort((a, b) => toNum(b.销售额 ?? b.sales) - toNum(a.销售额 ?? a.sales))
  const names = sorted.map(i => String(i.类目 ?? i.category ?? i.name ?? '-'))
  const values = sorted.map(i => toNum(i.销售额 ?? i.sales))
  const total = values.reduce((s, v) => s + v, 0)
  let cum = 0
  const cumulative = values.map(v => {
    cum += v
    return total > 0 ? cum / total : 0
  })

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['销售额', '累计占比'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: [
      { type: 'value', name: '销售额', splitLine: { lineStyle: { type: 'dashed' } } },
      { type: 'value', name: '累计占比', max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } }
    ],
    series: [
      { name: '销售额', type: 'bar', data: values, itemStyle: { color: '#5E6AD2', borderRadius: [4, 4, 0, 0] } },
      { name: '累计占比', type: 'line', yAxisIndex: 1, data: cumulative, smooth: true, lineStyle: { width: 2, color: '#2E335E' }, symbol: 'none' }
    ]
  }
}

// ─── Overview: Daily Sales Trend ───

export function buildDailySalesTrendOption(
  dailySales?: Array<Record<string, unknown>> | null
): EChartsOption {
  if (!dailySales?.length) return {}
  const rows = [...dailySales].sort((a, b) => String(a.日期 ?? a.date).localeCompare(String(b.日期 ?? b.date)))
  const dates = rows.map(i => String(i.日期 ?? i.date))
  const amounts = rows.map(i => toNum(i.销售额 ?? i.sales ?? i.amount))

  // Compute moving average window based on series length
  const window = rows.length > 60 ? 30 : rows.length > 14 ? 7 : 3
  const ma = amounts.map((_, idx) => {
    const start = Math.max(0, idx - window + 1)
    const slice = amounts.slice(start, idx + 1)
    return slice.reduce((s, v) => s + v, 0) / slice.length
  })

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['日销售额', `${window}日均值`], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: dates, boundaryGap: false, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [
      { name: '日销售额', type: 'line', data: amounts, smooth: true, showSymbol: false, lineStyle: { width: 2, color: '#5E6AD2' }, areaStyle: { color: 'rgba(94, 106, 210, 0.08)' } },
      { name: `${window}日均值`, type: 'line', data: ma, smooth: true, showSymbol: false, lineStyle: { width: 2, color: '#2E335E', type: 'dashed' } }
    ]
  }
}

// ─── Segment: Contribution Bar ───

export function buildSegmentContributionOption(
  profiles?: SegmentProfile[] | null
): EChartsOption {
  if (!profiles?.length) return {}
  const names = profiles.map(p => String(p.分群 ?? p.cluster_id ?? '-'))
  const population = profiles.map(p => toNum(p.人数占比))
  const sales = profiles.map(p => toNum(p.销售贡献占比))

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['人数占比', '销售贡献占比'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: names },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` }, splitLine: { lineStyle: { type: 'dashed' } } },
    series: [
      { name: '人数占比', type: 'bar', data: population, itemStyle: { color: '#5E6AD2', borderRadius: [4, 4, 0, 0] } },
      { name: '销售贡献占比', type: 'bar', data: sales, itemStyle: { color: '#2E335E', borderRadius: [4, 4, 0, 0] } }
    ]
  }
}

// ─── Segment: Radar Profile ───

export function buildSegmentRadarOption(
  profiles?: SegmentProfile[] | null
): EChartsOption {
  if (!profiles?.length) return {}
  // Find numeric fields excluding identifiers and counts
  const first = profiles[0]
  const numericKeys = Object.keys(first).filter(k => {
    if (['分群', 'cluster_id', 'cluster_name', '人数', 'customer_count'].includes(k)) return false
    const v = first[k]
    return typeof v === 'number' && Number.isFinite(v)
  })
  if (!numericKeys.length) return {}

  // Normalize each indicator to max=1 across segments
  const maxValues: Record<string, number> = {}
  numericKeys.forEach(k => {
    maxValues[k] = Math.max(...profiles.map(p => Math.abs(toNum(p[k]))), 1e-6)
  })

  const indicators = numericKeys.map(k => ({ name: k, max: 1 }))
  const seriesData = profiles.map(p => ({
    value: numericKeys.map(k => toNum(p[k]) / maxValues[k]),
    name: String(p.分群 ?? p.cluster_id ?? '-')
  }))

  return {
    tooltip: {},
    legend: { bottom: 0, data: seriesData.map(d => d.name) },
    radar: {
      indicator: indicators,
      radius: '65%',
      axisName: { fontSize: 10 }
    },
    series: [{
      type: 'radar',
      data: seriesData,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2 }
    }]
  }
}

// ─── Segment: K-Scan ───

export function buildKScanOption(
  kscan?: KScanPoint[] | null
): EChartsOption {
  if (!kscan?.length) return {}
  const ks = kscan.map(p => p.k ?? 0)
  const silhouettes = kscan.map(p => p.轮廓系数 ?? 0)
  const hasDb = kscan.some(p => p['DB指数'] !== undefined)

  const legendData = ['轮廓系数']
  const series: any[] = [{
    name: '轮廓系数',
    type: 'line',
    data: silhouettes,
    smooth: true,
    lineStyle: { width: 2, color: '#5E6AD2' },
    symbol: 'circle',
    symbolSize: 6
  }]

  if (hasDb) {
    legendData.push('DB指数')
    const dbValues = kscan.map(p => p['DB指数'] ?? 0)
    // Normalize DB index for visual comparison (lower is better, invert)
    const maxDb = Math.max(...dbValues, 1e-6)
    series.push({
      name: 'DB指数',
      type: 'line',
      data: dbValues.map(v => maxDb > 0 ? v / maxDb : 0),
      smooth: true,
      lineStyle: { width: 2, color: '#2E335E', type: 'dashed' },
      symbol: 'diamond',
      symbolSize: 6
    })
  }

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: legendData, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: ks, name: 'K' },
    yAxis: { type: 'value', name: '得分', splitLine: { lineStyle: { type: 'dashed' } } },
    series
  }
}

// ─── Association: Rule Bubble ───

export function buildAssociationBubbleOption(
  rules?: AssociationRule[] | null
): EChartsOption {
  if (!rules?.length) return {}
  const data = rules.map(r => [toNum(r.置信度), toNum(r.提升度), toNum(r.支持度)])

  return {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const [conf, lift, sup] = params.data
        return `置信度: ${(conf * 100).toFixed(1)}%<br>提升度: ${lift.toFixed(2)}<br>支持度: ${(sup * 100).toFixed(2)}%`
      }
    },
    grid: { left: '3%', right: '7%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: { type: 'value', name: '置信度', axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` }, splitLine: { lineStyle: { type: 'dashed' } } },
    yAxis: { type: 'value', name: '提升度', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [{
      type: 'scatter',
      data,
      symbolSize: (d: number[]) => Math.sqrt(d[2]) * 200 + 4,
      itemStyle: { color: '#5E6AD2', opacity: 0.7 }
    }]
  }
}

// ─── Association: HUIM Top Bundles ───

export function buildHuimBarOption(
  huim?: HuimItem[] | null
): EChartsOption {
  if (!huim?.length) return {}
  const sorted = [...huim].sort((a, b) => toNum(b.总效用) - toNum(a.总效用)).slice(0, 15)
  const names = sorted.map(i => String(i.组合 ?? '-'))
  const values = sorted.map(i => toNum(i.总效用))

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '5%', containLabel: true },
    xAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 10 } },
    series: [{
      type: 'bar' as const,
      data: values,
      itemStyle: { color: '#5E6AD2', borderRadius: [0, 4, 4, 0] }
    }]
  }
}

// ─── Recommendation: Model Metrics ───

export function buildRecommendationMetricsOption(
  evaluation?: EvaluationMetric[] | null
): EChartsOption {
  if (!evaluation?.length) return {}
  const metrics = ['Precision@10', 'Recall@10', 'HitRate@10', 'NDCG@10', 'Coverage', 'NDCG']
  const availableMetrics = metrics.filter(m => evaluation.some(e => e[m] !== undefined))
  if (!availableMetrics.length) return {}

  const models = evaluation.map(e => e.model ?? '-')

  const series = availableMetrics.map((metric, idx) => {
    const colors = ['#5E6AD2', '#2E335E', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']
    return {
      name: metric,
      type: 'bar' as const,
      data: evaluation.map(e => toNum(e[metric])),
      itemStyle: { color: colors[idx % colors.length], borderRadius: [4, 4, 0, 0] }
    }
  })

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: availableMetrics, bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: models },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series
  }
}

// ─── Recommendation: Signal Reliability ───

export function buildReliabilityOption(
  reliability?: Record<string, number> | null
): EChartsOption {
  if (!reliability || !Object.keys(reliability).length) return {}
  const entries = Object.entries(reliability)
  const names = entries.map(([k]) => k)
  const values = entries.map(([, v]) => v)

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: names },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [{
      type: 'bar' as const,
      data: values,
      itemStyle: { color: '#5E6AD2', borderRadius: [4, 4, 0, 0] }
    }]
  }
}

// ─── Promotion: Naive vs DML Effect ───

export function buildPromotionEffectOption(
  payload?: PromotionPayload | null
): EChartsOption {
  if (!payload || (payload.naive_diff === undefined && payload.dml_ate === undefined)) return {}
  const categories = ['Naive Diff', 'DML ATE']
  const values = [toNum(payload.naive_diff), toNum(payload.dml_ate)]

  const series: any[] = [{
    name: '效应值',
    type: 'bar',
    data: values,
    itemStyle: {
      color: (params: any) => params.dataIndex === 0 ? '#94A3B8' : '#5E6AD2',
      borderRadius: [4, 4, 0, 0]
    }
  }]

  // Add CI error bar for DML if available
  if (payload.dml_ci && Array.isArray(payload.dml_ci) && payload.dml_ci.length === 2) {
    const [lo, hi] = payload.dml_ci
    const ate = toNum(payload.dml_ate)
    series.push({
      name: '95% CI',
      type: 'custom',
      data: [[1, ate]],
      renderItem: (_params: any, api: any) => {
        const x = api.coord([api.value(0), api.value(1)])[0]
        const yLo = api.coord([0, lo])[1]
        const yHi = api.coord([0, hi])[1]
        const halfWidth = 12
        return {
          type: 'group',
          children: [
            { type: 'line', shape: { x1: x, y1: yLo, x2: x, y2: yHi }, style: { stroke: '#2E335E', lineWidth: 2 } },
            { type: 'line', shape: { x1: x - halfWidth, y1: yLo, x2: x + halfWidth, y2: yLo }, style: { stroke: '#2E335E', lineWidth: 2 } },
            { type: 'line', shape: { x1: x - halfWidth, y1: yHi, x2: x + halfWidth, y2: yHi }, style: { stroke: '#2E335E', lineWidth: 2 } }
          ]
        }
      }
    })
  }

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['效应值', '95% CI'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: categories },
    yAxis: { type: 'value', name: '效应', splitLine: { lineStyle: { type: 'dashed' } } },
    series
  }
}

// ─── Promotion: Discount Levels ───

export function buildDiscountLevelsOption(
  discountLevels?: DiscountLevel[] | null
): EChartsOption {
  if (!discountLevels?.length) return {}
  const names = discountLevels.map(d => String(d.discount ?? '-'))
  const values = discountLevels.map(d => toNum(d.avg_amount))

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: names, name: '折扣档位' },
    yAxis: { type: 'value', name: '平均金额', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [{
      type: 'bar' as const,
      data: values,
      itemStyle: { color: '#5E6AD2', borderRadius: [4, 4, 0, 0] }
    }]
  }
}
