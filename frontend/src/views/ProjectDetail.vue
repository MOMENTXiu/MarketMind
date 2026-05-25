<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/utils/http'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { VideoPlay, ArrowLeft, User, ShoppingCart, TrendCharts, Search } from '@element-plus/icons-vue'

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
    const { data } = await http.get(`/api/projects/${route.params.id}/`)
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
    const { data } = await http.post(`/api/projects/${route.params.id}/reanalyze/`)
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
    const { data } = await http.get(`/api/projects/${project.value?.id}/customers/`, {
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
    const { data } = await http.get('/api/recommend/item/', { params: { item: selectedAntecedent.value } })
    // API返回的是 {upstream, downstream, target_customers}
    // 前置商品 -> 后置商品 = downstream（下游）
    recommendedItems.value = data.downstream || []
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
    const { data } = await http.post('/api/recommend/calculate/', { item: selectedAntecedent.value })
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

const speakAnalysis = async (type: string, data: any) => {
  const key = `${type}_${data.cluster_id ?? 'global'}`
  console.log(`[Clustering TTS] 开始播报`, { type, key, data })

  voiceLoading.value[key] = true
  try {
    const savedLLM = localStorage.getItem('llm_config')
    const savedTTS = localStorage.getItem('tts_config')
    if (!savedLLM) {
      ElMessage.warning('请先在设置页面配置 AI 模型')
      router.push('/settings')
      return
    }

    const llmConfig = JSON.parse(savedLLM)
    const ttsConfig = savedTTS ? JSON.parse(savedTTS) : null
    console.log('[Clustering TTS] 配置:', { llmConfig: { provider: llmConfig.provider, model: llmConfig.modelName }, ttsConfig })

    // 使用后端的 AI Voice API，支持 OpenAI 和 Claude
    console.log('[Clustering TTS] 发送请求到 /api/ai-voice/broadcast/')
    const { data: voiceData } = await http.post('/api/ai-voice/broadcast/', {
      data,
      llm_config: llmConfig,
      tts_config: ttsConfig,
      scene_type: type === 'cluster' || type === 'list' ? 'clustering' : 'summary'
    })

    console.log('[Clustering TTS] 收到响应:', voiceData)

    if (voiceData.success) {
      subtitleText.value = voiceData.text
      console.log('[Clustering TTS] LLM生成文本:', voiceData.text)

      currentAudioUrl.value = voiceData.audio_url
      console.log('[Clustering TTS] 音频URL:', voiceData.audio_url)

      setTimeout(() => {
        if (audioRef.value) {
          console.log('[Clustering TTS] 准备播放音频, audioRef存在:', !!audioRef.value)
          console.log('[Clustering TTS] Audio src:', audioRef.value.src)

          audioRef.value.play().then(() => {
            console.log('[Clustering TTS] 音频播放成功')
            showSubtitle.value = true
          }).catch(err => {
            console.error('[Clustering TTS] 音频播放失败:', err)
            ElMessage.error('音频播放失败: ' + err.message)
          })
        } else {
          console.error('[Clustering TTS] audioRef不存在')
        }
      }, 100)
    } else {
      console.error('[Clustering TTS] 响应success=false')
    }
  } catch (error: any) {
    console.error('[Clustering TTS] 请求失败:', error)
    console.error('[Clustering TTS] 错误详情:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status
    })
    const msg = error.response?.data?.detail || error.message
    ElMessage.error(`播报失败: ${msg}`)
  } finally {
    voiceLoading.value[key] = false
  }
}

const stopAudio = () => {
  if (audioRef.value) {
    audioRef.value.pause()
  }

  // 暂停后5秒自动消失
  setTimeout(() => {
    if (audioRef.value && audioRef.value.paused) {
      showSubtitle.value = false
    }
  }, 5000)
}

// 提取会员姓名（从name字段中移除ID部分）
const extractName = (fullName: string) => {
  // 假设格式是 "姓名-ID" 或直接是姓名
  const parts = fullName.split('-')
  return parts[0] || fullName
}

const fmtCurrency = (val?: number) => (val === undefined || val === null || Number.isNaN(val)) ? '-' : `${val.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`

onMounted(() => { loadProject() })
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
              <span class="m-value">{{ project?.dataset_filename }}</span>
            </div>
            
            <div class="mini-divider"></div>
            
            <div class="meta-segment">
              <span class="m-label">处理状态：</span>
              <div class="status-wrap-micro">
                <span class="status-dot-nano" :class="project?.status"></span>
                <span class="m-value">{{ project?.status }}</span>
              </div>
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
            <div v-if="!selectedClusterId && selectedClusterId !== 0" class="cluster-grid-layout">
              <div v-for="cluster in clusterProfiles" :key="cluster.cluster_id" class="cluster-card-modern">
                <div class="card-head">
                  <span class="badge">Group {{ cluster.cluster_id + 1 }}</span>
                  <el-button 
                    circle size="small" 
                    class="btn-voice"
                    @click.stop="speakAnalysis('cluster', cluster)"
                    :loading="voiceLoading[`cluster_${cluster.cluster_id}`]"
                  >
                    <el-icon v-if="!voiceLoading[`cluster_${cluster.cluster_id}`]"><VideoPlay /></el-icon>
                  </el-button>
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

    <!-- Subtitle Overlay -->
    <transition name="subtitle-fade">
      <div class="voice-subtitle" v-if="showSubtitle">
        <div class="sub-content">
          <div class="indicator"><span></span><span></span><span></span></div>
          <p>{{ subtitleText }}</p>
          <button class="stop-btn" @click="stopAudio" title="停止播报">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="6" width="12" height="12" rx="2"/>
            </svg>
          </button>
        </div>
      </div>
    </transition>

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

    <audio ref="audioRef" :src="currentAudioUrl" @ended="showSubtitle = false" class="hidden-audio"></audio>
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

.status-dot-nano.已完成 { background: #10b981; }
.status-dot-nano.处理中 { background: #f59e0b; }
.status-dot-micro.失败 { background: #ef4444; }

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

/* Subtitle */
.voice-subtitle { position: fixed; bottom: 40px; left: 0; right: 0; display: flex; justify-content: center; z-index: 2000; }
.sub-content { background: rgba(0,0,0,0.85); backdrop-filter: blur(12px); padding: 12px 32px; border-radius: 40px; display: flex; align-items: center; gap: 16px; color: white; max-width: 80%; }
.indicator { display: flex; gap: 3px; }
.indicator span { width: 3px; height: 12px; background: #10B981; animation: jump 1s infinite; }
@keyframes jump { 50% { height: 4px; } }

/* Subtitle Transitions */
.subtitle-fade-enter-active, .subtitle-fade-leave-active {
  transition: all 0.4s var(--ease-spring);
}
.subtitle-fade-enter-from, .subtitle-fade-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.stop-btn {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.5);
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #ef4444;
  transition: all 0.2s;
  flex-shrink: 0;
}

.stop-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  border-color: #ef4444;
  transform: scale(1.1);
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

.hidden-audio { display: none; }
</style>