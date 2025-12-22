<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { Refresh, Download, VideoPlay, VideoPause, ArrowLeft, Connection, User, ShoppingCart, TrendCharts } from '@element-plus/icons-vue'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const route = useRoute()
const router = useRouter()

// --- Interfaces ---
interface ForecastRow { week: number; date?: string; sales: number; profit: number; profit_rate?: number }
interface ForecastSummary { total_sales: number; total_profit: number; avg_profit_rate: number }
interface ClusterProfile { cluster_id: number; cluster_name: string; customer_count: number; avg_recency: number; avg_frequency: number; avg_monetary: number; avg_order_value: number; marketing_strategy: string }
interface Project { id: string; name: string; description?: string; dataset_filename?: string; status: string; created_at: string; updated_at: string; parameters: any; results?: { association_rules?: any[]; prediction_data?: { sales_r2?: number; profit_r2?: number; train_samples?: number; forecast_weeks?: number; forecast_data?: ForecastRow[]; forecast_summary?: ForecastSummary }; clustering_data?: { total_customers?: number; n_clusters?: number; silhouette_score?: number; cluster_profiles?: ClusterProfile[]; contribution?: any[]; cluster_customers?: any }; audio_path?: string; report_path?: string }; error_message?: string }

// --- State ---
const project = ref<Project | null>(null)
const loading = ref(false)
const audioRef = ref<HTMLAudioElement>()
const currentAudioUrl = ref('')

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

// Voice Logic
const voiceLoading = ref<Record<string, boolean>>({})
const subtitleText = ref('')
const showSubtitle = ref(false)

// --- Computed ---
const associationRules = computed(() => project.value?.results?.association_rules || [])
const clusteringData = computed(() => project.value?.results?.clustering_data || null)
const clusterProfiles = computed(() => clusteringData.value?.cluster_profiles || [])
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

// --- Methods ---
const loadProject = async () => {
  loading.value = true
  try {
    const { data } = await axios.get(`/api/projects/${route.params.id}`)
    if (data.success) project.value = data.data
  } catch (error) { 
    ElMessage.error('加载项目失败')
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
    const { data } = await axios.post(`/api/projects/${route.params.id}/reanalyze`)
    if (data.success) {
      ElMessage.success('重新分析任务已启动')
      setTimeout(loadProject, 1000)
    }
  } catch (e) {}
}

const fetchClusterCustomers = async (clusterId: number) => {
  selectedClusterId.value = clusterId
  customersLoading.value = true
  try {
    const { data } = await axios.get(`/api/projects/${project.value?.id}/customers`, {
      params: { cluster_id: clusterId }
    })
    if (data.success) clusterCustomers.value = data.data
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
    const { data } = await axios.get('/api/recommend/item', { params: { item: selectedAntecedent.value } })
    recommendedItems.value = data.recommends || []
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
    const { data } = await axios.post('/api/recommend/calculate', { item: selectedAntecedent.value })
    if (data.success) {
      recommendedItems.value = data.rules
      ElMessage.success(`计算完成，发现 ${data.rules.length} 条新规则`)
    }
  } catch (e) {
    ElMessage.error('实时计算失败')
  } finally {
    calcLoading.value = false
  }
}

const showCustomerRec = async (customer: any) => {
  selectedCustomer.value = customer
  showRecommendationDialog.value = true
  recsLoading.value = true
  try {
    const { data } = await axios.get('/api/recommend/user', { params: { user_id: customer.id } })
    customerRecs.value = data.recommends || []
  } catch (e) {
    console.error('Fetch rec error', e)
  } finally {
    recsLoading.value = false
  }
}

const speakAnalysis = async (type: string, data: any) => {
  const key = `${type}_${data.cluster_id ?? 'global'}`
  voiceLoading.value[key] = true
  try {
    const savedLLM = localStorage.getItem('llm_config')
    if (!savedLLM) throw new Error('未配置 LLM')
    const llmConfig = JSON.parse(savedLLM)
    const prompt = `你是一位商业顾问。请将以下算法数据转化为一段简短、专业、富有行动建议的中文播报词（50字以内）。严禁输出代码或 JSON。
数据内容: ${JSON.stringify(data)}`
    const llmRes = await axios.post(`${llmConfig.baseUrl}/chat/completions`, {
      model: llmConfig.modelName,
      messages: [{ role: 'user', content: prompt }]
    }, { headers: { 'Authorization': `Bearer ${llmConfig.apiKey}` } })
    const text = llmRes.data.choices[0].message.content.trim()
    subtitleText.value = text
    const { data: ttsData } = await axios.post('/api/voice/tts', { text })
    if (ttsData.success) {
      currentAudioUrl.value = ttsData.audio_url
      setTimeout(() => { audioRef.value?.play(); showSubtitle.value = true }, 100)
    }
  } catch (error: any) {
    ElMessage.error(`播报失败: ${error.message}`)
  } finally { voiceLoading.value[key] = false }
}

const stopAudio = () => { if (audioRef.value) audioRef.value.pause(); showSubtitle.value = false }
const fmtCurrency = (val?: number) => (val === undefined || val === null || Number.isNaN(val)) ? '-' : `${val.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`

onMounted(() => { loadProject() })
</script>

<template>
  <div class="project-detail-layout" v-loading="loading">
    <div class="container-breath-fixed">
      <!--Navbar -->
      <header class="detail-navbar">
        <div class="header-left">
          <button class="btn-back-round" @click="$router.push('/projects')">
            <el-icon><ArrowLeft /></el-icon>
          </button>
          <div class="project-info-minimal">
            <h1>{{ project?.name }}</h1>
            <div class="meta-tags">
              <span class="tag-pill">{{ project?.dataset_filename }}</span>
              <span class="tag-pill status">{{ project?.status }}</span>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <el-button @click="reanalyze" :loading="project?.status === '处理中'" plain round>重新分析</el-button>
          <el-button type="primary" round @click="$router.push(`/projects/${project?.id}/recommend`)">智能查询</el-button>
        </div>
      </header>

      <main v-if="project" class="detail-content-flow">
        <!-- 1. KPI & Forecast Bento -->
        <section class="section-block grid-dashboard">
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

        <!-- 2. Association Rules (The "Missing" Part) -->
        <section class="section-block association-section">
          <div class="section-header-modern">
            <div class="title-with-icon">
              <el-icon class="icon-main"><ShoppingCart /></el-icon>
              <div>
                <h3>购物篮关联分析</h3>
                <p>发现商品间的隐藏购买规律</p>
              </div>
            </div>
          </div>

          <!-- Lookup Tool -->
          <div class="association-lookup-bar">
            <div class="lookup-input">
              <label>🔍 关联查询</label>
              <el-select v-model="selectedAntecedent" filterable placeholder="选择前置商品..." @change="updateRecommendation" class="full-width">
                <el-option v-for="item in antecedentOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </div>
            <div class="lookup-arrow" v-if="selectedAntecedent">→</div>
            <div class="lookup-results" v-loading="recLoading">
              <div v-if="recommendedItems.length > 0" class="rec-pills">
                <div v-for="rec in recommendedItems" :key="rec.consequent" class="rec-pill-item">
                  <span class="name">{{ rec.consequent }}</span>
                  <span class="prob">{{ (rec.confidence * 100).toFixed(0) }}%</span>
                </div>
              </div>
              <div v-else-if="selectedAntecedent" class="rec-empty-state">
                <span>暂无推荐</span>
                <el-button type="primary" size="small" @click="calculateRealtimeRules" :loading="calcLoading">⚡ 实时计算</el-button>
              </div>
              <div v-else class="lookup-placeholder">请选择商品查看 AI 推荐</div>
            </div>
          </div>

          <!-- All Rules Grid -->
          <div class="rules-grid-dashboard">
            <div v-for="(rule, idx) in associationRules.slice(0, 12)" :key="idx" class="mini-rule-card">
              <div class="rule-flow">
                <div class="antecedents"><span v-for="a in rule.antecedents" :key="a" class="a-tag">{{ a }}</span></div>
                <el-icon class="arrow"><ShoppingCart /></el-icon>
                <div class="consequent"><span class="c-tag">{{ rule.consequent }}</span></div>
              </div>
              <div class="rule-meta">提升度 {{ rule.lift.toFixed(2) }}</div>
            </div>
          </div>
        </section>

        <!-- 3. Customer Clusters -->
        <section class="section-block clustering-section">
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
            <div v-if="!selectedClusterId" class="cluster-grid-layout">
              <div v-for="cluster in clusterProfiles" :key="cluster.cluster_id" class="cluster-card-modern">
                <div class="card-head">
                  <span class="badge">Group {{ cluster.cluster_id }}</span>
                  <el-button circle size="small" class="btn-voice" @click="speakAnalysis('cluster', cluster)" :loading="voiceLoading[`cluster_${cluster.cluster_id}`]">🔊</el-button>
                </div>
                <h4>{{ cluster.cluster_name }}</h4>
                <div class="kpis">
                  <div class="kpi"><span>{{ cluster.customer_count }}</span>人</div>
                  <div class="kpi">¥<span>{{ fmtCurrency(cluster.avg_order_value) }}</span>价</div>
                </div>
                <p class="strat">{{ cluster.marketing_strategy }}</p>
                <el-button type="primary" class="btn-action" @click="fetchClusterCustomers(cluster.cluster_id)">管理名单</el-button>
              </div>
            </div>

            <!-- List View -->
            <div v-else class="cluster-list-view">
              <div class="list-head">
                <el-button link @click="selectedClusterId = null" :icon="ArrowLeft">返回聚类</el-button>
                <div class="cluster-info">
                  <h2>{{ selectedCluster?.cluster_name }}</h2>
                  <el-button round size="small" @click="speakAnalysis('list', selectedCluster)" :loading="voiceLoading[`list_${selectedClusterId}`]">🔊 总结播报</el-button>
                </div>
              </div>
              <div class="table-container">
                <el-table :data="clusterCustomers" v-loading="customersLoading" height="500">
                  <el-table-column prop="id" label="ID" width="140" />
                  <el-table-column prop="recency" label="R (天)" sortable />
                  <el-table-column prop="frequency" label="F (次)" sortable />
                  <el-table-column prop="monetary" label="M (金额)" sortable>
                    <template #default="{ row }">¥{{ fmtCurrency(row.monetary) }}</template>
                  </el-table-column>
                  <el-table-column label="操作" width="140" fixed="right">
                    <template #default="{ row }">
                      <el-button size="small" round @click="showCustomerRec(row)">推荐</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
          </transition>
        </section>
      </main>
    </div>

    <!-- Subtitle Overlay -->
    <div class="voice-subtitle" v-if="showSubtitle" @click="stopAudio">
      <div class="sub-content">
        <div class="indicator"><span></span><span></span><span></span></div>
        <p>{{ subtitleText }}</p>
      </div>
    </div>

    <!-- Dialog -->
    <el-dialog v-model="showRecommendationDialog" :title="`客户建议: ${selectedCustomer?.id}`" width="400px">
      <div v-loading="recsLoading" class="rec-modal">
        <div v-if="customerRecs.length" class="rec-rows">
          <div v-for="rec in customerRecs" :key="rec.item" class="rec-row">
            <span>{{ rec.item }}</span>
            <b>{{ (rec.score * 100).toFixed(0) }}%</b>
          </div>
        </div>
        <el-empty v-else description="暂无数据" :image-size="40" />
      </div>
    </el-dialog>

    <audio ref="audioRef" :src="currentAudioUrl" @ended="showSubtitle = false" class="hidden-audio"></audio>
  </div>
</template>

<style scoped>
.project-detail-layout { min-height: 100vh; background: #F8F9FA; padding-bottom: 100px; }
html.dark .project-detail-layout { background: #0D0D0F; }
.container-breath-fixed { max-width: 1200px; margin: 0 auto; padding: 0 24px; }

.detail-navbar { height: 100px; display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; gap: 20px; align-items: center; }
.btn-back-round { width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--border-subtle); background: white; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.project-info-minimal h1 { font-size: 1.5rem; font-weight: 800; margin: 0; }
.tag-pill { font-size: 0.7rem; padding: 2px 8px; background: rgba(0,0,0,0.05); border-radius: 10px; color: #666; margin-right: 8px; }

.section-block { background: white; border-radius: 32px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.02); margin-bottom: 32px; border: 1px solid rgba(0,0,0,0.02); }
html.dark .section-block { background: #161618; border-color: rgba(255,255,255,0.05); }

/* Dashboard Grid */
.grid-dashboard { display: grid; grid-template-columns: 300px 1fr; gap: 32px; }
.stats-col { display: flex; flex-direction: column; gap: 16px; }
.metric-card-glass { background: var(--color-bg-base); padding: 24px; border-radius: 24px; }
.m-label { font-size: 0.75rem; color: var(--text-tertiary); font-weight: 600; margin-bottom: 4px; }
.m-value { font-size: 1.6rem; font-weight: 800; }
.chart-col { display: flex; flex-direction: column; }
.dashboard-chart { height: 300px; width: 100%; }

/* Headers */
.section-header-modern { margin-bottom: 32px; }
.title-with-icon { display: flex; gap: 16px; align-items: center; }
.icon-main { font-size: 24px; padding: 12px; background: var(--color-accent-soft); color: var(--color-accent); border-radius: 16px; }
.title-with-icon h3 { font-size: 1.4rem; font-weight: 800; margin: 0; }
.title-with-icon p { font-size: 0.9rem; color: var(--text-tertiary); margin: 4px 0 0 0; }

/* Association Lookup */
.association-lookup-bar { display: flex; align-items: center; gap: 24px; background: var(--color-bg-base); padding: 24px; border-radius: 24px; margin-bottom: 32px; flex-wrap: wrap; }
.lookup-input { flex: 1; min-width: 200px; }
.lookup-input label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-tertiary); margin-bottom: 8px; }
.lookup-results { flex: 2; min-width: 300px; }
.rec-pills { display: flex; gap: 12px; flex-wrap: wrap; }
.rec-pill-item { background: white; padding: 8px 16px; border-radius: 30px; display: flex; gap: 12px; align-items: center; box-shadow: var(--shadow-sm); }
html.dark .rec-pill-item { background: #252528; }
.rec-pill-item .prob { font-weight: 800; color: var(--color-accent); font-size: 0.8rem; }

/* Rules Grid */
.rules-grid-dashboard { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.mini-rule-card { background: var(--color-bg-base); padding: 16px; border-radius: 16px; border: 1px solid rgba(0,0,0,0.03); }
.rule-flow { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.a-tag { font-size: 0.75rem; background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px; margin-right: 4px; }
.c-tag { font-size: 0.75rem; background: var(--color-accent-soft); color: var(--color-accent); padding: 2px 6px; border-radius: 4px; font-weight: 700; }
.rule-meta { font-size: 0.7rem; color: var(--text-tertiary); }

/* Clusters */
.cluster-grid-layout { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
.cluster-card-modern { background: var(--color-bg-base); border-radius: 24px; padding: 24px; display: flex; flex-direction: column; transition: 0.3s; }
.cluster-card-modern:hover { transform: translateY(-8px); box-shadow: var(--shadow-md); }
.card-head { display: flex; justify-content: space-between; margin-bottom: 16px; }
.cluster-card-modern h4 { font-size: 1.3rem; margin: 0 0 16px 0; }
.kpis { display: flex; gap: 20px; margin-bottom: 16px; }
.kpi { font-weight: 700; font-size: 1rem; }
.kpi span { color: var(--color-accent); }
.strat { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; flex: 1; margin-bottom: 20px; }
.btn-action { height: 44px !important; border-radius: 12px !important; font-weight: 700 !important; }

/* Drill down */
.list-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 24px; }
.cluster-info h2 { font-size: 2rem; margin: 0; }
.table-container { border-radius: 24px; overflow: hidden; background: white; }

/* Subtitle */
.voice-subtitle { position: fixed; bottom: 40px; left: 0; right: 0; display: flex; justify-content: center; z-index: 2000; }
.sub-content { background: rgba(0,0,0,0.85); backdrop-filter: blur(12px); padding: 12px 32px; border-radius: 40px; display: flex; align-items: center; gap: 16px; color: white; max-width: 80%; cursor: pointer; }
.indicator { display: flex; gap: 3px; }
.indicator span { width: 3px; height: 12px; background: #10B981; animation: jump 1s infinite; }
@keyframes jump { 50% { height: 4px; } }

.hidden-audio { display: none; }
</style>