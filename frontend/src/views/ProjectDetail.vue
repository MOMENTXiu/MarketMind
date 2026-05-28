<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, ScatterChart, CustomChart, RadarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent, RadarComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { ArrowLeft, User, ShoppingCart, TrendCharts, Search, MagicStick, Folder, UploadFilled } from '@element-plus/icons-vue'
import {
  getAnalysisArtifactPayload,
  getApiErrorMessage,
  getRetailArtifactPayload,
  getRetailProject,
  getRetailProjectStatusConfig,
  isActiveRetailProjectStatus,
  listRetailArtifacts,
  listRetailRecommendations,
  normalizeRetailProjectStatus,
  openRetailProjectEvents,
  runRetailAnalysis,
  uploadRetailDataset,
  regularizeProjectDataset,
  type AnalysisSseEvent,
  type ApiRef
} from '../api'
import DpKpiStrip from '../components/data-processing/DpKpiStrip.vue'
import DpOverviewCharts from '../components/data-processing/DpOverviewCharts.vue'
import DpSegmentCharts from '../components/data-processing/DpSegmentCharts.vue'
import DpAssociationCharts from '../components/data-processing/DpAssociationCharts.vue'
import DpRecommendationCharts from '../components/data-processing/DpRecommendationCharts.vue'
import DpPromotionCharts from '../components/data-processing/DpPromotionCharts.vue'

use([CanvasRenderer, LineChart, BarChart, ScatterChart, CustomChart, RadarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, RadarComponent])

const route = useRoute()
const router = useRouter()
const projectId = computed(() => String(route.params.id))

// --- Interfaces ---
interface ForecastRow { week: number; date?: string; sales: number; profit: number; profit_rate?: number }
interface ForecastSummary { total_sales: number; total_profit: number; avg_profit_rate: number }
interface ClusterProfile { cluster_id: number; cluster_name: string; customer_count: number; avg_recency: number; avg_frequency: number; avg_monetary: number; avg_order_value: number; marketing_strategy: string }
interface Project { id: string; name: string; description?: string; analysis_kind?: string | null; dataset_filename?: string; dataset_ref?: { name?: string } | null; status: string; created_at: string; updated_at: string; parameters?: any; summary?: Record<string, any>; quality_summary?: Record<string, any>; artifact_refs?: any[]; recommendations?: any[]; marketer_insights?: Record<string, any[]>; stage_statuses?: any[]; results?: { association_rules?: any[]; prediction_data?: { sales_r2?: number; profit_r2?: number; train_samples?: number; forecast_weeks?: number; forecast_data?: ForecastRow[]; forecast_summary?: ForecastSummary }; clustering_data?: { total_customers?: number; n_clusters?: number; silhouette_score?: number; cluster_profiles?: ClusterProfile[]; contribution?: any[]; cluster_customers?: any }; report_path?: string }; error?: string; error_message?: string }

// --- State ---
const project = ref<Project | null>(null)
const loading = ref(false)
const artifacts = ref<ApiRef[]>([])
const associationRuleRows = ref<Array<Record<string, unknown>>>([])
const customerSegmentRows = ref<Array<Record<string, unknown>>>([])
const customerProfileRows = ref<Array<Record<string, unknown>>>([])
let pollingTimer: number | undefined
let projectEventSource: EventSource | undefined

// Drill-down State
const selectedClusterId = ref<number | null>(null)
const clusterCustomers = ref<any[]>([])
const customersLoading = ref(false)
const showRecommendationDialog = ref(false)
const selectedCustomer = ref<any>(null)
const customerRecs = ref<any[]>([])
const recsLoading = ref(false)

// Association Lookup State
const selectedAntecedent = ref('')
const recommendedItems = ref<any[]>([])
const recLoading = ref(false)
const calcLoading = ref(false)

// --- Computed ---
const toNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const associationRules = computed(() => {
  if (associationRuleRows.value.length) {
    return associationRuleRows.value
      .map((row) => {
        const antecedentText = String(row['前项'] ?? row.antecedents ?? '')
        const antecedents = antecedentText
          .split('+')
          .map(item => item.trim())
          .filter(Boolean)
        return {
          antecedents,
          consequent: String(row['后项'] ?? row.consequent ?? ''),
          confidence: toNumber(row['置信度'] ?? row.confidence),
          lift: toNumber(row['提升度'] ?? row.lift, 1)
        }
      })
      .filter(rule => rule.antecedents.length > 0 && rule.consequent)
  }
  return project.value?.results?.association_rules || []
})
const clusteringData = computed(() => project.value?.results?.clustering_data || null)
const clusterProfiles = computed(() => {
  const legacyProfiles = clusteringData.value?.cluster_profiles || []
  if (legacyProfiles.length) return legacyProfiles
  const segments = project.value?.marketer_insights?.segment_value || []
  return segments.map((segment: any, index: number) => ({
    cluster_id: Number(segment.cluster_id ?? index),
    cluster_name: String(segment.cluster_name ?? segment.segment ?? `Group ${index + 1}`),
    customer_count: Number(segment.customer_count ?? segment.count ?? 0),
    avg_recency: Number(segment.avg_recency ?? 0),
    avg_frequency: Number(segment.avg_frequency ?? 0),
    avg_monetary: Number(segment.avg_monetary ?? segment.monetary ?? 0),
    avg_order_value: Number(segment.avg_order_value ?? segment.avg_monetary ?? 0),
    marketing_strategy: String(segment.marketing_strategy ?? segment.strategy ?? '暂无分群策略')
  }))
})
const selectedCluster = computed(() => clusterProfiles.value.find(p => p.cluster_id === selectedClusterId.value))

const antecedentOptions = computed(() => {
  const items = new Set<string>()
  associationRules.value.forEach((rule: any) => {
    rule.antecedents.forEach((item: string) => items.add(item))
  })
  return Array.from(items).sort()
})

const forecastOption = computed(() => {
  const rows = project.value?.results?.prediction_data?.forecast_data || []
  if (!rows.length) return {}
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.9)', borderRadius: 8, padding: 12 },
    legend: { bottom: 0, icon: 'circle' },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: rows.map(i => `第${i.week}周`), boundaryGap: false, axisLine: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [
      { name: '销售额', type: 'line', smooth: true, data: rows.map(i => i.sales), lineStyle: { width: 3, color: '#2E335E' }, areaStyle: { color: 'rgba(46, 51, 94, 0.05)' } },
      { name: '利润', type: 'line', smooth: true, data: rows.map(i => i.profit), lineStyle: { width: 3, color: '#5E6AD2' } }
    ]
  }
})

const projectStatusConfig = computed(() => getRetailProjectStatusConfig(project.value?.status))
const projectStatusClass = computed(() => normalizeRetailProjectStatus(project.value?.status))
const isProjectRunning = computed(() => isActiveRetailProjectStatus(project.value?.status))
const visibleArtifactRefs = computed(() => artifacts.value.length ? artifacts.value : (project.value?.artifact_refs || []))
interface DpKvRow { label: string; value: string }
const safeNum = (v: unknown, fallback: number | null = null): number | null => {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}
const numShort = (v: unknown): string => {
  const n = safeNum(v)
  if (n === null) return '-'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 10_000) return `${(n / 10_000).toFixed(2)}万`
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}
const pctLabel = (v: unknown): string => {
  const n = safeNum(v)
  return n !== null ? `${(n * 100).toFixed(1)}%` : '-'
}
const currencyShort = (v: unknown): string => {
  const n = safeNum(v)
  if (n === null) return '-'
  if (n >= 1_000_000) return `¥${(n / 1_000_000).toFixed(2)}M`
  if (n >= 10_000) return `¥${(n / 10_000).toFixed(2)}万`
  return `¥${n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
}

const datasetSummaryRows = computed((): DpKvRow[] => {
  if (!isDataProcessingProject.value) return []
  const stats = (dpOverview.value?.overview ?? dpSummary.value?.基础销售统计) as Record<string, unknown> | undefined
  const rows: DpKvRow[] = []
  if (project.value?.dataset_filename) rows.push({ label: '数据集', value: project.value.dataset_filename })
  if (stats?.['总记录数'] !== undefined) rows.push({ label: '总记录数', value: numShort(stats['总记录数']) })
  if (stats?.['用户数'] !== undefined) rows.push({ label: '用户数', value: numShort(stats['用户数']) })
  if (stats?.['商品数'] !== undefined) rows.push({ label: '商品数', value: numShort(stats['商品数']) })
  if (stats?.['订单数'] !== undefined) rows.push({ label: '订单数', value: numShort(stats['订单数']) })
  if (stats?.['总销售额'] !== undefined) rows.push({ label: '总销售额', value: currencyShort(stats['总销售额']) })
  if (stats?.['客单价'] !== undefined) rows.push({ label: '客单价', value: currencyShort(stats['客单价']) })
  if (stats?.['退货率'] !== undefined) rows.push({ label: '退货率', value: pctLabel(stats['退货率']) })
  const seg = dpSummary.value?.顾客画像 as Record<string, unknown> | undefined
  if (seg?.['分群数'] !== undefined) rows.push({ label: '分群数', value: numShort(seg['分群数']) })
  const rec = dpSummary.value?.个性化推荐 as Record<string, unknown> | undefined
  if (rec?.['最佳模型'] !== undefined) rows.push({ label: '最佳模型', value: String(rec['最佳模型']) })
  return rows
})

const qualityGridRows = computed((): DpKvRow[] => {
  const q = project.value?.quality_summary ?? {}
  const rows: DpKvRow[] = []
  if (q['raw_rows'] !== undefined) rows.push({ label: '原始行数', value: numShort(q['raw_rows']) })
  if (q['normalized_rows'] !== undefined) rows.push({ label: '标准化行数', value: numShort(q['normalized_rows']) })
  if (q['duplicate_rows_removed'] !== undefined) rows.push({ label: '去重行数', value: numShort(q['duplicate_rows_removed']) })
  if (q['mapped_field_count'] !== undefined) rows.push({ label: '字段映射数', value: numShort(q['mapped_field_count']) })
  const fields = q['available_standard_fields'] as string[] | undefined
  if (fields) rows.push({ label: '标准字段覆盖', value: numShort(fields.length) })
  const mr = q['missing_rates'] as Record<string, unknown> | undefined
  if (mr) {
    const maxRate = Math.max(...Object.values(mr).map(v => safeNum(v, 0) ?? 0))
    rows.push({ label: '最大缺失率', value: pctLabel(maxRate) })
  }
  if (q['invalid_date_count'] !== undefined) rows.push({ label: '无效日期', value: numShort(q['invalid_date_count']) })
  if (q['invalid_amount_count'] !== undefined) rows.push({ label: '无效金额', value: numShort(q['invalid_amount_count']) })
  const score = safeNum(q['analysis_ready_score'], 0) ?? 0
  const gradeLabel = q['grade'] ?? (score >= 0.8 ? '优秀' : score >= 0.6 ? '良好' : '需检查')
  if (gradeLabel) rows.push({ label: '质量状态', value: String(gradeLabel) })
  return rows.length ? rows : Object.entries(q).slice(0, 8).map(([k, v]) => ({ label: k, value: formatValue(v) }))
})

const summaryEntries = computed(() => Object.entries(project.value?.summary || {}).filter(([k]) => k !== 'analysis_kind' && k !== 'job_id').slice(0, 8))
const qualityEntries = computed(() => Object.entries(project.value?.quality_summary || {}).slice(0, 8))
const stageStatuses = computed(() => project.value?.stage_statuses || [])

// Data Processing specific
const isDataProcessingProject = computed(() => project.value?.analysis_kind === 'data_processing')
const needsReview = computed(() => project.value?.status === 'needs_review')
const isRetailProject = computed(() => !isDataProcessingProject.value)

// Data Processing payloads
const dpSummary = ref<Record<string, any> | null>(null)
const dpOverview = ref<Record<string, any> | null>(null)
const dpSegments = ref<Record<string, any> | null>(null)
const dpAssociation = ref<Record<string, any> | null>(null)
const dpRecommendation = ref<Record<string, any> | null>(null)
const dpPromotion = ref<Record<string, any> | null>(null)
const dpPayloadsLoading = ref(false)

const formatValue = (value: unknown) => {
  if (value === undefined || value === null || value === '') return '-'
  if (typeof value === 'number') return Number.isFinite(value) ? value.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '-'
  if (typeof value === 'string') return value
  if (typeof value === 'boolean') return value ? '是' : '否'
  return JSON.stringify(value)
}

const normalizeArtifacts = (payload: { artifacts?: ApiRef[] } | ApiRef[]) => {
  return Array.isArray(payload) ? payload : (payload.artifacts || [])
}

const findArtifactId = (name: string) => {
  const refs = artifacts.value.length ? artifacts.value : (project.value?.artifact_refs || [])
  return refs.find(ref => ref.id === `table:${name}` || ref.name === name)?.id
}

const loadArtifactRows = async (name: string) => {
  const artifactId = findArtifactId(name)
  if (!artifactId) return []
  const payload = await getRetailArtifactPayload(projectId.value, artifactId)
  return payload.rows || []
}

const loadDetailPayloads = async () => {
  const [rules, segments, profiles] = await Promise.all([
    loadArtifactRows('retail_item_association_rules.csv').catch(() => []),
    loadArtifactRows('retail_customer_segments.csv').catch(() => []),
    loadArtifactRows('retail_customer_profile.csv').catch(() => [])
  ])
  associationRuleRows.value = rules
  customerSegmentRows.value = segments
  customerProfileRows.value = profiles
}

const findJsonArtifactId = (pattern: string) => {
  const refs = artifacts.value.length ? artifacts.value : (project.value?.artifact_refs || [])
  return refs.find(ref => ref.id?.includes(pattern))?.id
}

const loadDataProcessingPayloads = async () => {
  if (!isDataProcessingProject.value) return
  dpPayloadsLoading.value = true
  try {
    const ids = {
      summary: findJsonArtifactId('universal_summary'),
      overview: findJsonArtifactId('universal_overview'),
      segments: findJsonArtifactId('universal_profile_segments'),
      association: findJsonArtifactId('universal_association'),
      recommendation: findJsonArtifactId('universal_recommendation'),
      promotion: findJsonArtifactId('universal_promotion')
    }
    const [
      summaryRes,
      overviewRes,
      segmentsRes,
      associationRes,
      recommendationRes,
      promotionRes
    ] = await Promise.all([
      ids.summary ? getAnalysisArtifactPayload(projectId.value, ids.summary).catch(() => null) : null,
      ids.overview ? getAnalysisArtifactPayload(projectId.value, ids.overview).catch(() => null) : null,
      ids.segments ? getAnalysisArtifactPayload(projectId.value, ids.segments).catch(() => null) : null,
      ids.association ? getAnalysisArtifactPayload(projectId.value, ids.association).catch(() => null) : null,
      ids.recommendation ? getAnalysisArtifactPayload(projectId.value, ids.recommendation).catch(() => null) : null,
      ids.promotion ? getAnalysisArtifactPayload(projectId.value, ids.promotion).catch(() => null) : null
    ])
    dpSummary.value = (summaryRes?.payload as Record<string, any>) ?? null
    dpOverview.value = (overviewRes?.payload as Record<string, any>) ?? null
    dpSegments.value = (segmentsRes?.payload as Record<string, any>) ?? null
    dpAssociation.value = (associationRes?.payload as Record<string, any>) ?? null
    dpRecommendation.value = (recommendationRes?.payload as Record<string, any>) ?? null
    dpPromotion.value = (promotionRes?.payload as Record<string, any>) ?? null
  } finally {
    dpPayloadsLoading.value = false
  }
}

const loadArtifacts = async () => {
  try {
    const payload = await listRetailArtifacts(projectId.value)
    artifacts.value = normalizeArtifacts(payload)
  } catch {
    artifacts.value = project.value?.artifact_refs || []
  }
}

const refreshProject = async () => {
  const data = await getRetailProject(projectId.value)
  project.value = data as Project
  if (!isActiveRetailProjectStatus(data.status)) {
    await loadArtifacts()
    if (isDataProcessingProject.value) {
      await loadDataProcessingPayloads()
    } else {
      await loadDetailPayloads()
    }
  }
}

const stopProjectPolling = () => {
  if (pollingTimer !== undefined) {
    window.clearInterval(pollingTimer)
    pollingTimer = undefined
  }
}

const stopProjectEvents = () => {
  if (projectEventSource) {
    projectEventSource.close()
    projectEventSource = undefined
  }
}

const parseAnalysisEvent = (event: MessageEvent<string>): AnalysisSseEvent | null => {
  try {
    return JSON.parse(event.data) as AnalysisSseEvent
  } catch {
    return null
  }
}

const startProjectEvents = () => {
  stopProjectPolling()
  stopProjectEvents()
  projectEventSource = openRetailProjectEvents(projectId.value)
  projectEventSource.onmessage = async (event) => {
    const payload = parseAnalysisEvent(event)
    if (payload?.heartbeat) return
    await refreshProject()
    if (payload?.terminal || !isProjectRunning.value) stopProjectEvents()
  }
  projectEventSource.addEventListener('state_changed', async (event) => {
    const payload = parseAnalysisEvent(event as MessageEvent<string>)
    await refreshProject()
    if (payload?.terminal || !isProjectRunning.value) stopProjectEvents()
  })
  projectEventSource.addEventListener('artifact_ready', async () => {
    await loadArtifacts()
    await refreshProject()
  })
  projectEventSource.onerror = async () => {
    stopProjectEvents()
    try {
      await refreshProject()
    } catch (error) {
      ElMessage.error(`刷新项目状态失败: ${getApiErrorMessage(error)}`)
    }
  }
}

// --- Methods ---
const loadProject = async () => {
  loading.value = true
  try {
    await refreshProject()
    if (isProjectRunning.value) startProjectEvents()
  } catch (error) {
    ElMessage.error(`加载项目失败: ${getApiErrorMessage(error)}`)
    router.push('/projects')
  } finally { loading.value = false }
}

const reanalyze = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要重新分析此项目吗？该操作将根据当前数据集重新生成所有模型与报告。',
      '重新分析确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    project.value = await runRetailAnalysis(projectId.value) as Project
    ElMessage.success('重新分析任务已启动')
    startProjectEvents()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(`启动失败: ${getApiErrorMessage(error)}`)
    }
  }
}

const fetchClusterCustomers = async (clusterId: number) => {
  selectedClusterId.value = clusterId
  customersLoading.value = true
  try {
    const profileByUser = new Map(
      customerProfileRows.value.map(row => [String(row.user_id ?? ''), row])
    )
    const segmentRows = customerSegmentRows.value.filter(row => {
      return toNumber(row.segment_id ?? row.cluster_id ?? row.cluster, -1) === clusterId
    })

    if (segmentRows.length) {
      clusterCustomers.value = segmentRows.map((row) => {
        const userId = String(row.user_id ?? row.customer_id ?? '')
        const profile = profileByUser.get(userId) || {}
        return {
          id: userId,
          name: userId,
          recency: toNumber(profile['R_最近购买间隔'] ?? profile.recency),
          frequency: toNumber(profile['F_购买频次'] ?? profile.frequency),
          monetary: toNumber(profile['M_消费金额'] ?? profile.monetary),
          cluster_id: clusterId
        }
      }).filter(row => row.id)
      return
    }

    const recommendations = project.value?.recommendations || []
    const seen = new Set<string>()
    clusterCustomers.value = recommendations
      .filter((recommendation: any) => {
        if (!recommendation.customer_id || seen.has(recommendation.customer_id)) return false
        seen.add(recommendation.customer_id)
        return true
      })
      .map((recommendation: any) => ({
        id: recommendation.customer_id,
        name: recommendation.customer_id,
        recency: 0,
        frequency: 0,
        monetary: 0,
        cluster_id: clusterId
      }))
  } catch (e) {
    ElMessage.error('获取客户列表失败')
  } finally {
    customersLoading.value = false
  }
}

const updateRecommendation = async () => {
  if (!selectedAntecedent.value) return
  recLoading.value = true
  try {
    const data = await listRetailRecommendations(projectId.value, { top_k: 100 })
    const recommendations = data.recommendations || []
    recommendedItems.value = recommendations
      .filter((recommendation: any) => recommendation.item !== selectedAntecedent.value)
      .map((recommendation: any) => ({
        item: recommendation.item,
        confidence: Number(recommendation.score) || 0,
        lift: 1,
        reason: recommendation.reason
      }))
      .slice(0, 8)
  } catch (e) {
    ElMessage.error('获取关联数据失败')
  } finally {
    recLoading.value = false
  }
}

const calculateRealtimeRules = async () => {
  if (!selectedAntecedent.value) return
  calcLoading.value = true
  try {
    recommendedItems.value = []
    ElMessage.info('暂无实时关联重算结果')
  } catch (e) {
    ElMessage.error('实时计算失败')
  } finally {
    calcLoading.value = false
  }
}

const reuploadFile = ref<HTMLInputElement | null>(null)

const triggerReupload = () => {
  reuploadFile.value?.click()
}

const handleReupload = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!/\.(csv|xls|xlsx)$/i.test(file.name)) {
    ElMessage.error('仅支持 CSV、XLS、XLSX 文件')
    return
  }
  try {
    await uploadRetailDataset(projectId.value, file)
    ElMessage.success('数据已重新上传，正在标准化...')
    const result = await regularizeProjectDataset(projectId.value)
    if (result.status === 'needs_review') {
      ElMessage.warning('数据标准化仍需审查')
    } else if (result.status === 'failed') {
      ElMessage.error(`标准化失败: ${result.error || '未知错误'}`)
    } else {
      ElMessage.success('标准化完成')
      await runRetailAnalysis(projectId.value)
      ElMessage.success('分析已启动')
      startProjectEvents()
    }
    await refreshProject()
  } catch (error) {
    ElMessage.error(`重新上传失败: ${getApiErrorMessage(error)}`)
  } finally {
    input.value = ''
  }
}

// 提取会员姓名（从name字段中移除ID部分）
const extractName = (fullName: string) => {
  // 假设格式是 "姓名-ID" 或直接是姓名
  const parts = fullName.split('-')
  return parts[0] || fullName
}

const fmtCurrency = (val?: number) => (val === undefined || val === null || Number.isNaN(val)) ? '-' : `${val.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`

onMounted(() => { loadProject() })
onUnmounted(() => {
  stopProjectPolling()
  stopProjectEvents()
})
</script>

<template>
  <div class="project-detail-layout" v-loading="loading">
    <div class="container-breath-fixed">
      <!--Navbar -->
      <header class="detail-navbar">
        <div class="header-left-aligned">
          <button class="btn-back-round" @click="$router.push('/projects')">
            <el-icon><ArrowLeft /></el-icon>
          </button>

          <h1 class="project-main-title">{{ project?.name }}</h1>

          <div class="mini-divider"></div>

          <div class="project-metadata-flow">
            <div class="meta-segment">
              <span class="m-label">源文件：</span>
              <span class="m-value">{{ project?.dataset_filename || project?.dataset_ref?.name || '无数据集' }}</span>
            </div>

            <div class="mini-divider"></div>

            <div class="meta-segment">
              <span class="m-label">处理状态：</span>
              <div class="status-wrap-micro">
                <span class="status-dot-nano" :class="projectStatusClass"></span>
                <span class="m-value">{{ projectStatusConfig.label }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <input
            ref="reuploadFile"
            type="file"
            accept=".csv,.xls,.xlsx"
            style="display: none"
            @change="handleReupload"
          >
          <el-button v-if="needsReview" @click="triggerReupload" type="warning" plain round>
            <el-icon style="margin-right: 4px"><UploadFilled /></el-icon>重新上传数据
          </el-button>
          <el-button v-if="!isDataProcessingProject" @click="reanalyze" :loading="isProjectRunning" plain round>重新分析</el-button>
          <el-button v-if="!isDataProcessingProject" type="primary" round @click="$router.push(`/projects/${project?.id}/recommend`)">智能查询</el-button>
        </div>
      </header>

      <main v-if="project" class="detail-content-flow">
        <!-- Needs Review Alert -->
        <el-alert
          v-if="needsReview"
          title="数据需要审查"
          :description="project.error || '数据标准化过程中发现需要人工审查的问题，请检查数据后重新上传。'"
          type="warning"
          show-icon
          :closable="false"
          style="margin-bottom: 24px; border-radius: 16px;"
        />

        <section class="section-block overview-section">
          <div class="section-header-modern compact">
            <div class="title-with-icon">
              <el-icon class="icon-main"><TrendCharts /></el-icon>
              <div>
                <h3>项目概览</h3>
                <p>{{ project.error || '诊断状态与数据集摘要' }}</p>
              </div>
            </div>
          </div>

          <div class="overview-grid">
            <!-- DP: dataset summary -->
            <template v-if="isDataProcessingProject">
              <div class="overview-panel">
                <h4>数据集摘要</h4>
                <div v-if="datasetSummaryRows.length" class="kv-list">
                  <div v-for="row in datasetSummaryRows" :key="row.label" class="kv-row">
                    <span>{{ row.label }}</span>
                    <strong>{{ row.value }}</strong>
                  </div>
                </div>
                <el-empty v-else description="暂无摘要" :image-size="56" />
              </div>
              <div class="overview-panel">
                <h4>数据质量</h4>
                <div v-if="qualityGridRows.length" class="kv-list">
                  <div v-for="row in qualityGridRows" :key="row.label" class="kv-row">
                    <span>{{ row.label }}</span>
                    <strong>{{ row.value }}</strong>
                  </div>
                </div>
                <el-empty v-else description="暂无质量数据" :image-size="56" />
              </div>
            </template>
            <!-- Retail: legacy -->
            <template v-else>
              <div class="overview-panel">
                <h4>摘要</h4>
                <div v-if="summaryEntries.length" class="kv-list">
                  <div v-for="([key, value]) in summaryEntries" :key="key" class="kv-row">
                    <span>{{ key }}</span>
                    <strong>{{ formatValue(value) }}</strong>
                  </div>
                </div>
                <el-empty v-else description="暂无摘要" :image-size="56" />
              </div>
              <div class="overview-panel">
                <h4>数据质量</h4>
                <div v-if="qualityEntries.length" class="kv-list">
                  <div v-for="([key, value]) in qualityEntries" :key="key" class="kv-row">
                    <span>{{ key }}</span>
                    <strong>{{ formatValue(value) }}</strong>
                  </div>
                </div>
                <el-empty v-else description="暂无质量数据" :image-size="56" />
              </div>
            </template>
          </div>

          <div class="stage-strip" v-if="stageStatuses.length">
            <div v-for="stage in stageStatuses" :key="stage.stage" class="stage-chip" :class="stage.status">
              <span>{{ stage.stage }}</span>
              <strong>{{ stage.status }}</strong>
            </div>
          </div>
        </section>

        <!-- Data Processing Dashboard -->
        <template v-if="isDataProcessingProject">
          <dp-kpi-strip :summary="dpSummary" />
          <dp-overview-charts :payload="dpOverview" />
          <dp-segment-charts :payload="dpSegments" />
          <dp-association-charts :payload="dpAssociation" />
          <dp-recommendation-charts :payload="dpRecommendation" />
          <dp-promotion-charts :payload="dpPromotion" />
        </template>

        <!-- 1. KPI & Forecast Bento (Retail only) -->
        <section v-if="isRetailProject" class="section-block grid-dashboard">
          <div class="stats-col">
            <div class="metric-card-glass">
              <div class="m-label">预测总销售额</div>
              <div class="m-value">¥{{ fmtCurrency(project.results?.prediction_data?.forecast_summary?.total_sales) }}</div>
            </div>
            <div class="metric-card-glass">
              <div class="m-label">预测总利润</div>
              <div class="m-value">¥{{ fmtCurrency(project.results?.prediction_data?.forecast_summary?.total_profit) }}</div>
            </div>
            <div class="metric-card-glass">
              <div class="m-label">分析客户基数</div>
              <div class="m-value">{{ project.results?.clustering_data?.total_customers }}</div>
            </div>
          </div>
          <div class="chart-col">
            <div class="section-header-inline">
              <h3><el-icon><TrendCharts /></el-icon> 销售趋势预估</h3>
            </div>
            <v-chart :option="forecastOption" autoresize class="dashboard-chart" />
          </div>
        </section>

        <section v-if="visibleArtifactRefs.length" class="section-block artifacts-section">
          <div class="section-header-modern compact">
            <div class="title-with-icon">
              <el-icon class="icon-main"><Folder /></el-icon>
              <div>
                <h3>{{ isDataProcessingProject ? '诊断信息' : '分析产物' }}</h3>
                <p>{{ isDataProcessingProject ? '原始 artifact refs 与调试输出' : '通过后端公开 ref 和 URL 访问' }}</p>
              </div>
            </div>
          </div>
          <div class="artifact-grid">
            <div v-for="ref in visibleArtifactRefs" :key="ref.id" class="artifact-card">
              <span class="artifact-type">{{ ref.type || 'artifact' }}</span>
              <strong>{{ ref.name || ref.id }}</strong>
              <small>{{ ref.id }}</small>
              <a v-if="ref.url" :href="ref.url" target="_blank" rel="noreferrer">打开</a>
            </div>
          </div>
        </section>

        <!-- 2. Association Rules (Retail only) -->
        <section v-if="isRetailProject" class="section-block association-section">
          <div class="section-header-modern">
            <div class="title-with-icon">
              <el-icon class="icon-main"><ShoppingCart /></el-icon>
              <div>
                <h3>购物篮关联分析</h3>
                <p>发现商品间的隐藏购买规律</p>
              </div>
            </div>
          </div>

          <div class="association-lookup-wrapper">
            <div class="lookup-label">
              <el-icon><ShoppingCart /></el-icon> 关联查询
            </div>

            <div class="lookup-controls">
              <el-select
                v-model="selectedAntecedent"
                filterable
                clearable
                placeholder="选择前置商品..."
                @change="updateRecommendation"
                class="premium-select"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
                <el-option v-for="item in antecedentOptions" :key="item" :label="item" :value="item" />
              </el-select>

              <div class="lookup-feedback" v-if="selectedAntecedent">
                <div v-if="recLoading" class="mini-pulse-loading">
                  <span></span><span></span><span></span>
                </div>
                <div v-else-if="recommendedItems.length > 0" class="rec-result-flow">
                  <div
                    v-for="rec in recommendedItems.slice(0, 3)"
                    :key="rec.item"
                    class="rec-tag-pill"
                    @click="router.push(`/projects/${route.params.id}/recommend?item=${encodeURIComponent(rec.item)}`)"
                  >
                    <span class="tag-name">{{ rec.item }}</span>
                    <span class="tag-prob">{{ (rec.confidence * 100).toFixed(0) }}%</span>
                  </div>
                </div>
                <div v-else class="rec-none">
                  <span class="none-text">无直接关联</span>
                  <el-button type="primary" size="small" @click="calculateRealtimeRules" :loading="calcLoading" class="btn-calculate-gradient">
                    <el-icon><MagicStick /></el-icon> 立即计算
                  </el-button>
                </div>
              </div>
              <div v-else class="lookup-hint">
                <span class="blinking-cursor">|</span> 选择商品查看 AI 推荐建议
              </div>
            </div>
          </div>

          <!-- All Rules Grid -->
          <div class="rules-grid-dashboard">
            <div
              v-for="(rule, idx) in associationRules.slice(0, 12)"
              :key="idx"
              class="mini-rule-card clickable"
              @click="router.push(`/projects/${project?.id}/recommend?item=${encodeURIComponent(rule.consequent)}`)"
            >
              <div class="rule-flow">
                <div class="antecedents"><span v-for="a in rule.antecedents" :key="a" class="a-tag">{{ a }}</span></div>
                <el-icon class="arrow"><ShoppingCart /></el-icon>
                <div class="consequent"><span class="c-tag">{{ rule.consequent }}</span></div>
              </div>
              <div class="rule-meta">提升度 {{ rule.lift.toFixed(2) }}</div>
            </div>
          </div>
        </section>

        <!-- 3. Customer Clusters (Retail only) -->
        <section v-if="isRetailProject" class="section-block clustering-section">
          <div class="section-header-modern">
            <div class="title-with-icon">
              <el-icon class="icon-main"><User /></el-icon>
              <div>
                <h3>客户画像聚类</h3>
                <p>基于 RFM 模型的客户价值分群</p>
              </div>
            </div>
          </div>

          <transition name="fade-transform" mode="out-in">
            <!-- Grid View -->
            <div v-if="!selectedClusterId && selectedClusterId !== 0" class="cluster-grid-layout">
              <div v-for="cluster in clusterProfiles" :key="cluster.cluster_id" class="cluster-card-modern">
                <div class="card-head">
                  <span class="badge">Group {{ cluster.cluster_id + 1 }}</span>
                </div>
                <h4>{{ cluster.cluster_name }}</h4>
                <div class="kpi-summary-row">
                  {{ cluster.customer_count }}人，平均 ¥{{ fmtCurrency(cluster.avg_order_value) }}。
                </div>
                <p class="strat">{{ cluster.marketing_strategy }}</p>
                <el-button type="primary" class="btn-action" @click="fetchClusterCustomers(cluster.cluster_id)">
                  查看客户名单
                </el-button>
              </div>
            </div>

            <!-- List View -->
            <div v-else class="cluster-list-view">
              <div class="list-head-modern">
                <el-button @click="selectedClusterId = null" :icon="ArrowLeft" circle class="btn-back-action" />
                <div class="list-title-group">
                  <span class="list-sub-label">分群客户详细名单</span>
                  <h2 class="list-main-title">{{ selectedCluster?.cluster_name }}</h2>
                </div>
              </div>
              <div class="table-container">
                <el-table
                  :data="clusterCustomers"
                  v-loading="customersLoading"
                  height="550"
                  row-class-name="clickable-row"
                  @row-click="(row: any) => router.push(`/projects/${project?.id}/customer/${row.id}`)"
                >
                  <el-table-column label="会员信息" width="200" fixed>
                    <template #default="{ row }">
                      <div class="user-info-cell">
                        <div class="u-name-primary">{{ extractName(row.name) }}</div>
                        <div class="u-id-secondary">ID {{ row.id }}</div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="recency" label="最后购买" sortable width="140">
                    <template #default="{ row }">
                      <span class="num-bold">{{ row.recency }}</span><span class="unit-label"> 天前</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="frequency" label="购买频次" sortable width="120">
                    <template #default="{ row }">
                      <span class="num-font">{{ row.frequency }}</span><span class="unit-label"> 次</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="monetary" label="累计消费" sortable min-width="160" align="right">
                    <template #default="{ row }">
                      <span class="monetary-val">¥{{ row.monetary.toFixed(2) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="100" fixed="right">
                    <template #default="{ row }">
                      <el-button size="small" round @click.stop="router.push(`/projects/${project?.id}/customer/${row.id}`)">详情</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
          </transition>
        </section>
      </main>
    </div>

    <!-- Personalized Recommendation & Detail Dialog -->
    <el-dialog
      v-model="showRecommendationDialog"
      :title="`客户画像详情`"
      width="520px"
      custom-class="premium-detail-dialog"
    >
      <div v-loading="recsLoading" class="detail-dialog-content">
        <!-- 1. Individual KPI Dashboard -->
        <div class="user-kpi-dashboard">
          <div class="u-kpi-card">
            <span class="u-label">累计消费</span>
            <span class="u-value">¥{{ fmtCurrency(selectedCustomer?.monetary) }}</span>
          </div>
          <div class="u-kpi-card">
            <span class="u-label">购买频次</span>
            <span class="u-value">{{ selectedCustomer?.frequency }} 次</span>
          </div>
          <div class="u-kpi-card">
            <span class="u-label">最后购买</span>
            <span class="u-value">{{ selectedCustomer?.recency }} 天前</span>
          </div>
        </div>

        <div class="detail-divider"></div>

        <!-- 2. Marketing Strategy Section -->
        <div class="marketing-strategy-section">
          <h4 class="strategy-header">
            <el-icon class="icon-align"><TrendCharts /></el-icon> 营销建议
          </h4>

          <div v-if="customerRecs.length" class="rec-grid-compact">
            <p class="strategy-text-relaxed">
              根据该客户在 <span class="group-highlight">Group {{ (selectedCustomer?.cluster_id ?? 0) + 1 }}</span> 的消费行为特征，建议采取以下精准触达方案：
            </p>
            <div class="rec-rows-modern">
              <div v-for="rec in customerRecs" :key="rec.item" class="rec-row-modern">
                <span class="item-name">{{ rec.item }}</span>
                <span class="item-reason">{{ rec.reason }}</span>
                <span class="item-prob">{{ (rec.score * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无特定建议" :image-size="60" />
        </div>
      </div>
    </el-dialog>

  </div>
</template>

<style scoped>
.project-detail-layout { min-height: 100vh; background: var(--color-bg-base); padding-bottom: 100px; }
html.dark .project-detail-layout { background: var(--color-bg-base); }
.container-breath-fixed { max-width: 1200px; margin: 0 auto; padding: 0 24px; }

.detail-navbar { height: 100px; display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; gap: 20px; align-items: center; }
.btn-back-round { width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--border-subtle); background: var(--color-surface); color: var(--text-primary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.3s; }
.btn-back-round:hover { transform: translateX(-4px); background: var(--color-surface-hover); }
.header-left-aligned {
  display: flex;
  align-items: center;
  gap: 16px;
}

.project-main-title {
  font-size: 1.5rem;
  font-weight: 850;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.02em;
}

.project-metadata-flow {
  display: flex;
  align-items: center;
  gap: 16px;
  background: transparent; /* Removed background */
}

.meta-segment {
  display: flex;
  align-items: center;
}

.m-label {
  font-size: 12px; /* text-xs */
  font-weight: 500;
  color: #64748b; /* text-gray-500 */
}

.m-value {
  font-size: 12px; /* text-xs */
  font-weight: 400; /* Regular weight */
  color: #94a3b8; /* text-gray-400 */
}

html.dark .m-value { color: #A1A1A6; }

.status-wrap-micro {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot-nano {
  width: 6px; /* w-1.5 */
  height: 6px; /* h-1.5 */
  border-radius: 50%;
  background: #94a3b8;
}

.status-dot-nano.queued { background: #94a3b8; }
.status-dot-nano.processing { background: #f59e0b; }
.status-dot-nano.completed { background: #10b981; }
.status-dot-nano.failed { background: #ef4444; }
.status-dot-nano.needs_review { background: #f97316; }

.mini-divider {
  width: 1px;
  height: 12px; /* h-3 */
  background: rgba(0, 0, 0, 0.1);
}

html.dark .mini-divider {
  background: rgba(255, 255, 255, 0.1);
}

.tag-pill { font-size: 0.7rem; padding: 2px 8px; background: rgba(0,0,0,0.05); border-radius: 10px; color: #666; margin-right: 8px; }

.section-block { background: var(--color-surface); border-radius: 32px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.02); margin-bottom: 32px; border: 1px solid var(--border-subtle); }
html.dark .section-block { background: var(--color-surface); border-color: var(--border-subtle); }

.section-header-modern.compact { margin-bottom: 20px; }
.overview-section { display: flex; flex-direction: column; gap: 24px; }
.overview-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.overview-panel { background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 20px; padding: 20px; min-height: 180px; }
.overview-panel h4 { margin: 0 0 14px 0; font-size: 0.9rem; color: var(--text-primary); }
.kv-list { display: flex; flex-direction: column; gap: 10px; }
.kv-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; font-size: 0.82rem; color: var(--text-tertiary); }
.kv-row strong { color: var(--text-primary); text-align: right; max-width: 55%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stage-strip { display: flex; flex-wrap: wrap; gap: 10px; }
.stage-chip { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 999px; background: var(--color-bg-base); border: 1px solid var(--border-subtle); font-size: 0.75rem; color: var(--text-tertiary); }
.stage-chip strong { color: var(--text-primary); }
.stage-chip.completed strong { color: #10b981; }
.stage-chip.processing strong { color: #f59e0b; }
.stage-chip.failed strong { color: #ef4444; }
.stage-chip.skipped strong { color: #94a3b8; }
.stage-chip.needs_review strong { color: #f97316; }
.artifact-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.artifact-card { display: flex; flex-direction: column; gap: 6px; background: var(--color-bg-base); border: 1px solid var(--border-subtle); border-radius: 18px; padding: 16px; min-height: 130px; }
.artifact-card strong { color: var(--text-primary); font-size: 0.95rem; }
.artifact-card small { color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.artifact-card a { margin-top: auto; color: var(--color-accent); font-weight: 700; font-size: 0.82rem; }
.artifact-type { width: fit-content; color: var(--color-accent); background: var(--color-accent-soft); border-radius: 999px; padding: 2px 8px; font-size: 0.7rem; font-weight: 800; }

/* Dashboard Grid */
.grid-dashboard { display: grid; grid-template-columns: 300px 1fr; gap: 32px; }
.stats-col { display: flex; flex-direction: column; gap: 16px; }
.metric-card-glass { background: var(--color-surface); padding: 24px; border-radius: 24px; border: 1px solid var(--border-subtle); }
.m-label { font-size: 0.75rem; color: var(--text-tertiary); font-weight: 600; margin-bottom: 4px; }
.m-value { font-size: 1.6rem; font-weight: 800; color: var(--text-primary); }
.chart-col { display: flex; flex-direction: column; }
.dashboard-chart { height: 300px; width: 100%; }

/* Headers */
.section-header-modern { margin-bottom: 32px; }
.title-with-icon { display: flex; gap: 16px; align-items: center; }
.icon-main { font-size: 24px; padding: 12px; background: var(--color-accent-soft); color: var(--color-accent); border-radius: 16px; }
.title-with-icon h3 { font-size: 1.4rem; font-weight: 800; margin: 0; color: var(--text-primary); }
.title-with-icon p { font-size: 0.9rem; color: var(--text-tertiary); margin: 4px 0 0 0; }

/* Association Lookup Refined */
.association-lookup-wrapper {
  display: flex;
  align-items: center;
  gap: 24px;
  background: var(--nav-pill-bg);
  backdrop-filter: blur(12px);
  padding: 12px 24px;
  border-radius: 20px;
  margin-bottom: 32px;
  border: 1px solid transparent;
  background-image: linear-gradient(var(--color-surface), var(--color-surface)),
                    linear-gradient(135deg, rgba(94, 106, 210, 0.2), rgba(167, 139, 250, 0.2));
  background-origin: border-box;
  background-clip: padding-box, border-box;
  box-shadow: var(--shadow-sm);
}

html.dark .association-lookup-wrapper {
  background-image: linear-gradient(var(--color-surface), var(--color-surface)),
                    linear-gradient(135deg, rgba(94, 106, 210, 0.1), rgba(167, 139, 250, 0.1));
}

.lookup-label {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.lookup-controls {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 1;
}

.premium-select {
  width: 240px !important;
}

.lookup-feedback {
  display: flex;
  align-items: center;
  flex: 1;
}

.rec-result-flow {
  display: flex;
  gap: 10px;
  animation: fadeIn 0.4s ease;
}

.rec-tag-pill {
  background: var(--color-bg-base);
  padding: 6px 14px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  border: 1px solid var(--border-subtle);
  transition: all 0.2s;
}

.rec-tag-pill:hover {
  transform: scale(1.05);
  border-color: var(--color-accent);
}

.tag-name { font-size: 0.85rem; font-weight: 700; color: var(--text-primary); }
.tag-prob { font-size: 0.75rem; font-weight: 800; color: var(--color-accent); }

.lookup-hint {
  font-size: 0.85rem;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.blinking-cursor {
  font-weight: 100;
  animation: blink 1s infinite;
  color: var(--color-accent);
}

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

.btn-calculate-gradient {
  background: linear-gradient(135deg, var(--color-brand) 0%, var(--color-accent) 100%) !important;
  border: none !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 12px rgba(94, 106, 210, 0.2) !important;
}

.mini-pulse-loading {
  display: flex;
  gap: 4px;
}

.mini-pulse-loading span {
  width: 6px;
  height: 6px;
  background: var(--color-accent);
  border-radius: 50%;
  animation: pulse-dot 1s infinite ease-in-out;
}

.mini-pulse-loading span:nth-child(2) { animation-delay: 0.2s; }
.mini-pulse-loading span:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse-dot { 0%, 100% { opacity: 0.3; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.2); } }

.rec-none {
  display: flex;
  align-items: center;
  gap: 16px;
}

.none-text { font-size: 0.85rem; font-style: italic; color: var(--text-tertiary); }

/* All Rules Grid */
.rules-grid-dashboard { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.mini-rule-card { background: var(--color-surface); padding: 16px; border-radius: 16px; border: 1px solid var(--border-subtle); transition: all 0.3s; }
.mini-rule-card.clickable { cursor: pointer; }
.mini-rule-card.clickable:hover { transform: translateY(-4px); border-color: var(--color-accent); box-shadow: 0 8px 16px rgba(94, 106, 210, 0.2); }
.rule-flow { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; color: var(--text-primary); }
.a-tag { font-size: 0.75rem; background: var(--nav-pill-bg); padding: 2px 6px; border-radius: 4px; margin-right: 4px; color: var(--text-secondary); }
.c-tag { font-size: 0.75rem; background: var(--color-accent-soft); color: var(--color-accent); padding: 2px 6px; border-radius: 4px; font-weight: 700; }
.rule-meta { font-size: 0.7rem; color: var(--text-tertiary); }

/* Clusters */
.cluster-grid-layout { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
.cluster-card-modern { background: var(--color-surface); border-radius: 24px; padding: 24px; display: flex; flex-direction: column; transition: 0.3s; border: 1px solid var(--border-subtle); position: relative; z-index: 1; }
.cluster-card-modern:hover { transform: translateY(-8px); box-shadow: var(--shadow-md); border-color: var(--color-accent); z-index: 2; }
.card-head { display: flex; justify-content: space-between; margin-bottom: 16px; position: relative; z-index: 3; }
.cluster-card-modern h4 { font-size: 1.3rem; margin: 0 0 12px 0; color: var(--text-primary); }
.kpi-summary-row { font-size: 1rem; font-weight: 700; color: var(--color-accent); margin-bottom: 16px; }
.strat { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; flex: 1; margin-bottom: 20px; }
.btn-action { height: 44px !important; border-radius: 12px !important; font-weight: 700 !important; position: relative; z-index: 3; pointer-events: auto; }

/* Drill down */
.list-head-modern {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 40px;
  animation: fadeIn 0.5s ease;
}

.btn-back-action {
  width: 48px;
  height: 48px;
  background: var(--color-surface) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
  box-shadow: var(--shadow-sm);
}

.btn-back-action:hover {
  transform: translateX(-4px);
  background: var(--color-bg-base) !important;
}

.list-title-group {
  display: flex;
  flex-direction: column;
}

.list-sub-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.list-main-title {
  font-size: 2.25rem;
  font-weight: 850;
  margin: 0;
  color: var(--text-primary);
  letter-spacing: -0.03em;
}

.table-container { border-radius: 24px; overflow: hidden; background: var(--color-surface); border: 1px solid var(--border-subtle); }

.user-info-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.u-name-primary {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.u-id-secondary {
  font-size: 0.75rem;
  color: #9ca3af;
}

html.dark .u-id-secondary {
  color: #6b7280;
}

.num-font {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 1.05rem;
}

.num-bold {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 1.05rem;
  color: var(--text-primary);
}

.unit-label {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.monetary-val {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  color: var(--text-primary);
  font-size: 1.1rem;
  letter-spacing: 0.02em;
}

:deep(.clickable-row) {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

:deep(.clickable-row:hover > td) {
  background-color: rgba(255, 255, 255, 0.05) !important;
}

html.dark :deep(.clickable-row:hover > td) {
  background-color: rgba(255, 255, 255, 0.03) !important;
}

/* Premium Detail Dialog Styles */
.detail-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.user-kpi-dashboard {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.u-kpi-card {
  background: var(--color-bg-base);
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

html.dark .u-kpi-card {
  background: #1E1E1E; /* Slightly brighter than #0A0A0A */
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.u-label {
  font-size: 0.7rem;
  color: var(--text-tertiary);
  font-weight: 600;
  text-transform: uppercase;
}

.u-value {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-primary);
}

.detail-divider {
  height: 1px;
  background: var(--border-subtle);
}

.strategy-header {
  font-size: 0.85rem;
  font-weight: 800;
  color: #60a5fa; /* text-blue-400 */
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-align {
  font-size: 1.1rem;
  vertical-align: middle;
}

.strategy-text-relaxed {
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 20px;
}

html.dark .strategy-text-relaxed {
  color: #A1A1A6; /* text-gray-400 */
}

.group-highlight {
  color: var(--color-accent);
  font-weight: 700;
}

.rec-rows-modern {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rec-row-modern {
  background: var(--color-bg-base);
  padding: 12px 16px;
  border-radius: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--border-subtle);
}

html.dark .rec-row-modern {
  background: #1E1E1E;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.item-name { font-weight: 700; color: var(--text-primary); }
.item-reason { font-size: 0.8rem; color: var(--text-tertiary); flex: 1; margin-left: 12px; }
.item-prob { font-weight: 800; color: var(--color-accent); font-size: 0.85rem; }

</style>
