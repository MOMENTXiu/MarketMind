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
import { Sunny, Moon } from '@element-plus/icons-vue'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const route = useRoute()
const router = useRouter()

interface ForecastRow {
  week: number
  date?: string
  sales: number
  profit: number
  profit_rate?: number
}

interface ForecastSummary {
  total_sales: number
  total_profit: number
  avg_profit_rate: number
}

interface ClusterProfile {
  cluster_id: number
  cluster_name: string
  customer_count: number
  avg_recency: number
  avg_frequency: number
  avg_monetary: number
  avg_order_value: number
  marketing_strategy: string
}

interface ClusterContribution {
  cluster_id: number
  total_sales: number
  total_profit: number
  sales_percentage: number
  profit_percentage: number
}

interface Project {
  id: string
  name: string
  description?: string
  dataset_filename?: string
  status: string
  created_at: string
  updated_at: string
  parameters: any
  results?: {
    association_rules?: any[]
    prediction_data?: {
      sales_r2?: number
      profit_r2?: number
      train_samples?: number
      forecast_weeks?: number
      forecast_data?: ForecastRow[]
      forecast_summary?: ForecastSummary
    }
    clustering_data?: {
      total_customers?: number
      n_clusters?: number
      silhouette_score?: number
      cluster_profiles?: ClusterProfile[]
      contribution?: ClusterContribution[]
    }
    audio_path?: string
    report_path?: string
  }
  error_message?: string
}

const project = ref<Project | null>(null)
const loading = ref(false)
const audioPlaying = ref(false)
const audioRef = ref<HTMLAudioElement>()

const associationRules = computed(() => project.value?.results?.association_rules || [])
const predictionData = computed(() => project.value?.results?.prediction_data || null)
const forecastSummary = computed(() => predictionData.value?.forecast_summary || null)
const forecastRows = computed(() => predictionData.value?.forecast_data || [])
const clusteringData = computed(() => project.value?.results?.clustering_data || null)
const clusterProfiles = computed(() => clusteringData.value?.cluster_profiles || [])
const clusterContribution = computed(() => clusteringData.value?.contribution || [])
const topClusters = computed(() => [...clusterProfiles.value].sort((a, b) => b.customer_count - a.customer_count).slice(0, 3))
const forecastOption = computed(() => {
  if (!forecastRows.value.length) return {}
  const weeks = forecastRows.value.map((i) => `第${i.week}周`)
  const sales = forecastRows.value.map((i) => i.sales)
  const profit = forecastRows.value.map((i) => i.profit)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['销售额', '利润'] },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: weeks, boundaryGap: false },
    yAxis: { type: 'value', name: '金额（元）' },
    series: [
      {
        name: '销售额',
        type: 'line',
        smooth: true,
        data: sales,
        symbolSize: 6,
        lineStyle: { width: 3 }
      },
      {
        name: '利润',
        type: 'line',
        smooth: true,
        data: profit,
        symbolSize: 6,
        lineStyle: { width: 3 }
      }
    ]
  }
})

// 加载项目详情
const loadProject = async () => {
  loading.value = true
  try {
    const response = await axios.get(`/api/projects/${route.params.id}`)
    if (response.data.success) {
      project.value = response.data.data
    }
  } catch (error) {
    ElMessage.error('加载项目失败')
    router.push('/projects')
  } finally {
    loading.value = false
  }
}

// 重新分析
const reanalyze = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要重新分析此项目吗？',
      '确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const response = await axios.post(`/api/projects/${route.params.id}/reanalyze`)
    if (response.data.success) {
      ElMessage.success('已开始重新分析')
      setTimeout(loadProject, 2000)
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

// 下载报告
const downloadReport = async () => {
  try {
    const response = await axios.get(
      `/api/projects/${route.params.id}/download/report`,
      { responseType: 'blob' }
    )

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${project.value?.name}_分析报告.md`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

// 播放语音
const playAudio = () => {
  if (audioRef.value) {
    if (audioPlaying.value) {
      audioRef.value.pause()
    } else {
      audioRef.value.play()
    }
  }
}

// 音频播放状态
const onAudioPlay = () => {
  audioPlaying.value = true
}

const onAudioPause = () => {
  audioPlaying.value = false
}

const onAudioEnded = () => {
  audioPlaying.value = false
}

// 状态标签类型
const statusType = computed(() => {
  const typeMap: Record<string, string> = {
    '待处理': 'info',
    '处理中': 'warning',
    '已完成': 'success',
    '失败': 'danger'
  }
  return typeMap[project.value?.status || ''] || 'info'
})

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 音频路径
const audioPath = computed(() => {
  if (project.value?.results?.audio_path) {
    return `/api/projects/${project.value.id}/audio`
  }
  return ''
})

const fmtCurrency = (val?: number) => {
  if (val === undefined || val === null || Number.isNaN(val)) return '-'
  return `${val.toLocaleString('zh-CN', { maximumFractionDigits: 2 })} 元`
}

const fmtPercent = (val?: number) => {
  if (val === undefined || val === null || Number.isNaN(val)) return '-'
  return `${val.toFixed(2)}%`
}

const fmtDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

// 跳转到商品推荐
const goRecommend = () => {
  if (project.value?.id) {
    router.push(`/projects/${project.value.id}/recommend`)
  }
}

// 主题切换
const theme = ref<'light' | 'dark'>('light')
const isDark = computed(() => theme.value === 'dark')

const applyTheme = () => {
  document.body.classList.toggle('dark-mode', isDark.value)
  localStorage.setItem('mm-theme', theme.value)
}

const toggleTheme = () => {
  theme.value = isDark.value ? 'light' : 'dark'
  applyTheme()
}

const loadTheme = () => {
  const stored = localStorage.getItem('mm-theme') as 'light' | 'dark' | null
  if (stored === 'dark') {
    theme.value = 'dark'
  }
  applyTheme()
}

// 定时刷新（处理中状态）
let refreshTimer: any = null

onMounted(() => {
  loadProject()

  refreshTimer = setInterval(() => {
    if (project.value?.status === '处理中') {
      loadProject()
    } else {
      clearInterval(refreshTimer)
    }
  }, 5000)
  loadTheme()
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<template>
  <div class="page-container" v-loading="loading">
    <el-page-header @back="$router.push('/projects')" title="返回">
      <template #content>
        <span class="page-title">
          📊 仪表盘<span v-if="project?.name"> ｜ {{ project.name }}</span>
        </span>
      </template>
      <template #extra v-if="project">
        <el-button
          circle
          :icon="isDark ? Sunny : Moon"
          @click="toggleTheme"
          :title="isDark ? '切换到明亮模式' : '切换到暗黑模式'"
        />
        <el-button type="primary" plain @click="goRecommend">
          🔗 商品推荐查询
        </el-button>
        <el-button @click="reanalyze" :disabled="project.status === '处理中'">
          🔄 重新分析
        </el-button>
        <el-button
          type="primary"
          @click="downloadReport"
          :disabled="!project.results?.report_path"
        >
          📥 下载报告
        </el-button>
      </template>
    </el-page-header>

    <div class="content" v-if="project">
      <!-- 顶部概要卡片 -->
      <div class="summary-grid">
        <el-card class="summary-card">
          <div class="summary-title">处理状态</div>
          <div class="summary-value">
            <el-tag :type="statusType" size="large">{{ project.status }}</el-tag>
          </div>
          <div class="summary-meta">{{ project.dataset_filename || '未上传数据集' }}</div>
        </el-card>

        <el-card class="summary-card" v-if="forecastSummary">
          <div class="summary-title">销售预测汇总</div>
          <div class="summary-value">{{ fmtCurrency(forecastSummary.total_sales) }}</div>
          <div class="summary-meta">预测总利润 {{ fmtCurrency(forecastSummary.total_profit) }}</div>
          <div class="summary-meta">平均利润率 {{ fmtPercent(forecastSummary.avg_profit_rate) }}</div>
        </el-card>
        <el-card class="summary-card" v-else>
          <div class="summary-title">销售预测</div>
          <div class="summary-desc muted">等待分析完成或无数据</div>
        </el-card>

        <el-card class="summary-card" v-if="clusteringData">
          <div class="summary-title">客户聚类</div>
          <div class="summary-value">{{ clusteringData.n_clusters || 0 }} 个群体</div>
          <div class="summary-meta">客户数 {{ clusteringData.total_customers || 0 }}</div>
          <div class="summary-meta">轮廓系数 {{ clusteringData.silhouette_score ?? 0 }}</div>
        </el-card>
        <el-card class="summary-card" v-else>
          <div class="summary-title">客户聚类</div>
          <div class="summary-desc muted">等待分析完成</div>
        </el-card>

      </div>

      <!-- 基本信息 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>项目信息</span>
            <el-tag :type="statusType" size="large">
              {{ project.status }}
            </el-tag>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目名称">
            {{ project.name }}
          </el-descriptions-item>
          <el-descriptions-item label="数据集">
            {{ project.dataset_filename || '未上传' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(project.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDate(project.updated_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="项目描述" :span="2">
            {{ project.description || '无' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="project.status === '失败'"
          type="error"
          title="分析失败"
          :description="project.error_message"
          style="margin-top: 1rem;"
          show-icon
        />

        <el-alert
          v-if="project.status === '处理中'"
          type="warning"
          title="正在分析中"
          description="系统正在分析您的数据，请耐心等待..."
          style="margin-top: 1rem;"
          show-icon
        />
      </el-card>

      <!-- 分析结果区域 -->
      <div v-if="project.status === '已完成' && project.results">
        <!-- 1. 关联规则分析 -->
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>📊 关联规则分析</span>
            </div>
          </template>

          <div v-if="associationRules.length > 0">
            <el-table :data="associationRules.slice(0, 10)" style="width: 100%">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column label="前项" min-width="150">
                <template #default="{ row }">
                  <el-tag
                    v-for="(item, index) in row.antecedents"
                    :key="index"
                    size="small"
                    class="mr-6"
                  >
                    {{ item }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="→" width="40" align="center" />
              <el-table-column prop="consequent" label="后项" min-width="120">
                <template #default="{ row }">
                  <el-tag type="success" size="small">{{ row.consequent }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="support" label="支持度" width="100">
                <template #default="{ row }">
                  {{ (row.support * 100).toFixed(2) }}%
                </template>
              </el-table-column>
              <el-table-column prop="confidence" label="置信度" width="100">
                <template #default="{ row }">
                  {{ (row.confidence * 100).toFixed(2) }}%
                </template>
              </el-table-column>
              <el-table-column prop="lift" label="提升度" width="100">
                <template #default="{ row }">
                  {{ row.lift.toFixed(2) }}
                </template>
              </el-table-column>
              <el-table-column prop="strategy" label="策略建议" min-width="220" show-overflow-tooltip />
            </el-table>
          </div>
          <el-empty v-else description="暂无关联规则数据" />
        </el-card>

        <!-- 2. 销售预测 -->
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>📈 销售预测</span>
            </div>
        </template>

          <div v-if="predictionData">
            <div class="stats-row">
              <div class="stat">
                <div class="stat-label">预测周数</div>
                <div class="stat-value">{{ predictionData.forecast_weeks }} 周</div>
              </div>
              <div class="stat">
                <div class="stat-label">销售额 R²</div>
                <div class="stat-value">{{ predictionData.sales_r2?.toFixed(4) || '-' }}</div>
              </div>
              <div class="stat">
                <div class="stat-label">利润 R²</div>
                <div class="stat-value">{{ predictionData.profit_r2?.toFixed(4) || '-' }}</div>
              </div>
              <div class="stat">
                <div class="stat-label">训练样本</div>
                <div class="stat-value">{{ predictionData.train_samples || 0 }}</div>
              </div>
            </div>

            <div class="chart-wrapper">
              <v-chart :option="forecastOption" autoresize class="chart" />
            </div>

            <el-table :data="forecastRows.slice(0, 10)" style="width: 100%; margin-top: 1rem;">
              <el-table-column prop="week" label="周次" width="70" />
              <el-table-column prop="date" label="日期" width="140">
                <template #default="{ row }">{{ fmtDate(row.date) }}</template>
              </el-table-column>
              <el-table-column prop="sales" label="预测销售额" min-width="140">
                <template #default="{ row }">{{ fmtCurrency(row.sales) }}</template>
              </el-table-column>
              <el-table-column prop="profit" label="预测利润" min-width="140">
                <template #default="{ row }">{{ fmtCurrency(row.profit) }}</template>
              </el-table-column>
              <el-table-column prop="profit_rate" label="利润率" width="100">
                <template #default="{ row }">{{ fmtPercent(row.profit_rate) }}</template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="销售预测数据不可用" />
        </el-card>

        <!-- 3. 客户聚类 -->
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>👥 客户聚类分析</span>
            </div>
          </template>

          <div v-if="clusteringData">
            <div class="stats-row">
              <div class="stat">
                <div class="stat-label">聚类数量</div>
                <div class="stat-value">{{ clusteringData.n_clusters }}</div>
              </div>
              <div class="stat">
                <div class="stat-label">客户总数</div>
                <div class="stat-value">{{ clusteringData.total_customers }}</div>
              </div>
              <div class="stat">
                <div class="stat-label">轮廓系数</div>
                <div class="stat-value">{{ clusteringData.silhouette_score }}</div>
              </div>
            </div>

            <div class="cluster-grid" v-if="clusterProfiles.length">
              <el-card v-for="profile in clusterProfiles" :key="profile.cluster_id" class="cluster-card">
                <div class="cluster-title">{{ profile.cluster_name }}</div>
                <div class="cluster-meta">{{ profile.customer_count }} 人</div>
                <div class="cluster-items">
                  <div class="item">平均R: {{ profile.avg_recency.toFixed(0) }} 天</div>
                  <div class="item">平均F: {{ profile.avg_frequency.toFixed(1) }} 次</div>
                  <div class="item">平均M: {{ fmtCurrency(profile.avg_monetary) }}</div>
                  <div class="item">客单价: {{ fmtCurrency(profile.avg_order_value) }}</div>
                </div>
                <div class="strategy">策略: {{ profile.marketing_strategy }}</div>
              </el-card>
            </div>

            <div style="margin-top: 1.5rem;">
              <h4>群体贡献度</h4>
              <el-table :data="clusterContribution" size="small">
                <el-table-column prop="cluster_id" label="ID" width="60" />
                <el-table-column prop="total_sales" label="销售额" min-width="120">
                  <template #default="{ row }">{{ fmtCurrency(row.total_sales) }}</template>
                </el-table-column>
                <el-table-column prop="total_profit" label="利润" min-width="120">
                  <template #default="{ row }">{{ fmtCurrency(row.total_profit) }}</template>
                </el-table-column>
                <el-table-column prop="sales_percentage" label="销售占比" width="120">
                  <template #default="{ row }">{{ fmtPercent(row.sales_percentage) }}</template>
                </el-table-column>
                <el-table-column prop="profit_percentage" label="利润占比" width="120">
                  <template #default="{ row }">{{ fmtPercent(row.profit_percentage) }}</template>
                </el-table-column>
              </el-table>
            </div>
          </div>
          <el-empty v-else description="客户聚类数据不可用" />
        </el-card>

      </div>

      <!-- 未完成提示 -->
      <el-card v-if="project.status !== '已完成'" class="result-card">
        <el-empty description="项目分析未完成，无法查看结果" />
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.5rem;
  font-weight: bold;
}

.content {
  margin-top: 2rem;
}

.info-card {
  margin-bottom: 2rem;
}

.result-card {
  margin-bottom: 2rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 1.1rem;
}

.audio-section {
  text-align: center;
  padding: 2rem;
}

.audio-player {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.audio-text {
  font-size: 1.1rem;
  color: #666;
}

.audio-text p {
  margin: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  background: #ffffff;
}

.summary-title {
  font-size: 0.95rem;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.summary-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: #0f172a;
}

.summary-meta {
  font-size: 0.95rem;
  color: #475569;
}

.summary-desc {
  font-size: 0.95rem;
}

.summary-desc.muted {
  color: #94a3b8;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.stat {
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.stat-label {
  color: #64748b;
  font-size: 0.95rem;
}

.stat-value {
  font-size: 1.2rem;
  font-weight: 700;
  color: #0f172a;
}

.chart-wrapper {
  margin-top: 1rem;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.5rem;
}

.chart {
  width: 100%;
  height: 320px;
}

.cluster-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
  margin: 1rem 0;
}

.cluster-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.cluster-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0f172a;
}

.cluster-meta {
  color: #475569;
  margin: 0.25rem 0 0.5rem;
}

.cluster-items {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.35rem;
  color: #334155;
  font-size: 0.95rem;
}

.strategy {
  margin-top: 0.75rem;
  color: #0f172a;
  font-size: 0.95rem;
}

.mr-6 {
  margin-right: 6px;
  margin-bottom: 4px;
}
</style>
