<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/utils/http'
import { ArrowLeft, User, ShoppingCart, MagicStick, VideoPlay } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const customerId = computed(() => route.params.customerId as string)
const projectId = computed(() => route.params.id as string)

const loading = ref(true)
const customer = ref<any>(null)
const recommendations = ref<any[]>([])
const purchasedItems = ref<any[]>([])
const aiAnalyzing = ref(false)
const aiSuggestion = ref('')
const voiceLoading = ref(false)
const audioRef = ref<HTMLAudioElement>()
const audioUrl = ref('')
const projectInfo = ref<any>(null)

const fetchCustomerDetail = async () => {
  loading.value = true
  try {
    const { data: projectData } = await http.get(`/api/analysis/projects/${projectId.value}`)
    if (projectData.success) {
      projectInfo.value = projectData.data
    }

    const { data: recData } = await http.get(`/api/analysis/projects/${projectId.value}/recommendations`, {
      params: { customer_id: customerId.value, top_k: 10 }
    })

    const recs = recData.data?.recommendations || []
    const clusterInfo = projectInfo.value?.marketer_insights?.segment_value?.[0] || null

    customer.value = {
      id: customerId.value,
      name: customerId.value,
      cluster_name: clusterInfo?.cluster_name || 'Retail V2 客户',
      cluster_id: clusterInfo?.cluster_id ?? 0,
      monetary: clusterInfo?.avg_monetary || 0,
      frequency: clusterInfo?.avg_frequency || 0,
      last_purchase: clusterInfo?.avg_recency || 0
    }

    recommendations.value = recs
    purchasedItems.value = []
  } catch (e) {
    console.error('Fetch customer detail error:', e)
    ElMessage.error('无法获取客户详情')
  } finally {
    loading.value = false
  }
}

// 生成AI建议文本（不播放语音）
const generateAISuggestion = async () => {
  if (aiAnalyzing.value) return
  aiAnalyzing.value = true
  try {
    const savedLLM = localStorage.getItem('llm_config')
    if (!savedLLM) {
      ElMessage.warning('请先在设置页面配置 AI 模型')
      router.push('/settings')
      return
    }

    const llmConfig = JSON.parse(savedLLM)

    // 使用后端的 AI Voice API，只要文本，不要语音
    const { data: voiceData } = await http.post('/api/ai-voice/broadcast/', {
      data: {
        customer_name: customer.value.name,
        customer_id: customer.value.id,
        cluster_name: customer.value.cluster_name,
        cluster_id: customer.value.cluster_id,
        monetary: customer.value.monetary,
        frequency: customer.value.frequency,
        recency: customer.value.last_purchase,
        recommendations: recommendations.value.map(r => ({
          item: r.item,
          score: r.score,
          reason: r.reason
        }))
      },
      llm_config: llmConfig,
      tts_config: null,
      scene_type: 'summary'
    })

    if (voiceData.success) {
      aiSuggestion.value = voiceData.text
    }
  } catch (error: any) {
    console.error('AI analysis error:', error)
    const msg = error.response?.data?.detail || error.message
    ElMessage.error(`AI 分析失败: ${msg}`)
  } finally {
    aiAnalyzing.value = false
  }
}

// 语音播报（可选功能）
const playVoice = async () => {
  if (!aiSuggestion.value) {
    ElMessage.warning('请先生成 AI 建议')
    return
  }
  if (voiceLoading.value) return

  voiceLoading.value = true
  try {
    const savedTTS = localStorage.getItem('tts_config')
    const ttsConfig = savedTTS ? JSON.parse(savedTTS) : {}

    const { data: ttsData } = await http.post('/api/voice/tts/', {
      text: aiSuggestion.value,
      voice: ttsConfig.voice,
      rate: ttsConfig.rate,
      volume: ttsConfig.volume
    })

    if (ttsData.success) {
      audioUrl.value = ttsData.audio_url

      setTimeout(() => {
        audioRef.value?.play()
      }, 100)
    }
  } catch (error: any) {
    ElMessage.error('语音播报失败')
  } finally {
    voiceLoading.value = false
  }
}

onMounted(async () => {
  await fetchCustomerDetail()
  // 自动触发AI分析（只生成文本，不播放语音）
  await generateAISuggestion()
})
</script>

<template>
  <div class="customer-analysis-page" v-loading="loading">
    <div class="container-breath-fixed">
      <header class="detail-header">
        <el-button @click="router.back()" :icon="ArrowLeft" circle class="btn-back-main" />
        <div class="header-titles">
          <h1 class="customer-name-title">
            <span class="name-text">{{ customer?.name || '加载中...' }}</span>
            <span class="badge-cluster">Group {{ (customer?.cluster_id ?? 0) + 1 }} | {{ customer?.cluster_name }}</span>
          </h1>
          <div class="project-subtitle-mini">
            所属项目: {{ projectInfo?.name || '...' }}
          </div>
        </div>
      </header>

      <main class="analysis-grid" v-if="customer">
        <!-- 1. Individual KPI Board -->
        <section class="kpi-board">
          <div class="glass-stat-card">
            <label>累计消费金额</label>
            <div class="val num-font">¥{{ customer.monetary?.toLocaleString() }}</div>
          </div>
          <div class="glass-stat-card">
            <label>历史购买频次</label>
            <div class="val num-font">{{ customer.frequency }} 次</div>
          </div>
          <div class="glass-stat-card">
            <label>所属消费分群</label>
            <div class="val highlight">{{ customer.cluster_name }}</div>
          </div>
        </section>

        <!-- 2. Marketing AI Section -->
        <section class="section-block ai-suggestion-card">
          <div class="card-header-iconic">
            <h3 class="suggestion-title"><el-icon><MagicStick /></el-icon> 营销建议</h3>
            <div class="action-buttons">
              <el-button
                round
                size="small"
                @click="generateAISuggestion"
                :loading="aiAnalyzing"
                :disabled="aiAnalyzing"
              >
                重新生成
              </el-button>
              <el-button
                type="primary"
                round
                size="small"
                @click="playVoice"
                :loading="voiceLoading"
                :disabled="!aiSuggestion || voiceLoading"
              >
                <el-icon style="margin-right: 4px"><VideoPlay /></el-icon>
                语音播报
              </el-button>
            </div>
          </div>
          <div class="ai-content-box">
            <!-- Skeleton Loading -->
            <div v-if="aiAnalyzing && !aiSuggestion" class="skeleton-loader">
              <div class="skeleton-line"></div>
              <div class="skeleton-line short"></div>
              <div class="skeleton-line medium"></div>
            </div>
            <!-- AI Content -->
            <p v-else-if="aiSuggestion" class="ai-text active">{{ aiSuggestion }}</p>
            <p v-else class="ai-text-placeholder">正在生成智能营销方案...</p>
          </div>
        </section>

        <!-- 3. Two Columns: Purchased vs Potential -->
        <div class="dual-columns">
          <section class="section-block column-card">
            <h3 class="col-title"><el-icon><ShoppingCart /></el-icon> 已购商品分析</h3>
            <div class="item-list-modern">
              <div
                v-for="item in purchasedItems"
                :key="item.name"
                class="modern-item clickable"
                @click="router.push(`/projects/${projectId}/recommend?item=${encodeURIComponent(item.name)}`)"
              >
                <div class="item-main">
                  <span class="name">{{ item.name }}</span>
                  <span class="meta">{{ item.category }} · {{ item.date }}</span>
                </div>
                <span class="price">¥{{ item.price }}</span>
              </div>
            </div>
          </section>

          <section class="section-block column-card highlight-border">
            <h3 class="col-title"><el-icon><User /></el-icon> 潜在需求预测</h3>
            <div class="item-list-modern">
              <div
                v-for="rec in recommendations"
                :key="rec.item"
                class="modern-item rec clickable"
                @click="router.push(`/projects/${projectId}/recommend?item=${encodeURIComponent(rec.item)}`)"
              >
                <div class="item-main">
                  <span class="name">{{ rec.item }}</span>
                  <span class="reason">{{ rec.reason }}</span>
                </div>
                <div class="prob-badge">{{ (rec.score * 100).toFixed(0) }}%</div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>

    <!-- Hidden Audio Element -->
    <audio ref="audioRef" :src="audioUrl" class="hidden-audio"></audio>
  </div>
</template>

<style scoped>
.customer-analysis-page { min-height: 100vh; background: var(--color-bg-base); padding-bottom: 80px; }
html.dark .customer-analysis-page { background: #0A0A0A; }
.container-breath-fixed { max-width: 1000px; margin: 0 auto; padding: 0 24px; }

.detail-header { height: 120px; display: flex; align-items: center; gap: 24px; margin-bottom: 24px; }
.btn-back-main { width: 48px; height: 48px; background: var(--color-surface) !important; border: 1px solid var(--border-subtle) !important; }

.header-titles { display: flex; flex-direction: column; gap: 2px; }

.customer-name-title {
  font-size: 2.25rem;
  font-weight: 850;
  margin: 0;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 16px;
}

.project-subtitle-mini {
  font-size: 0.7rem;
  color: var(--text-tertiary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.7;
}

.badge-cluster {
  font-size: 0.85rem;
  background: var(--color-accent-soft);
  color: var(--color-accent);
  padding: 4px 14px;
  border-radius: 12px;
  font-weight: 700;
  border: 1px solid rgba(94, 106, 210, 0.1);
}

.kpi-board { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 32px; }
.glass-stat-card { background: var(--color-surface); padding: 24px; border-radius: 24px; border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); }
.glass-stat-card label { font-size: 0.75rem; font-weight: 700; color: var(--text-tertiary); display: block; margin-bottom: 8px; }
.glass-stat-card .val { font-size: 1.5rem; font-weight: 850; color: var(--text-primary); }
.glass-stat-card .val.highlight { color: var(--color-accent); }

.section-block { background: var(--color-surface); border-radius: 24px; padding: 28px; border: 1px solid var(--border-subtle); margin-bottom: 24px; }
.ai-suggestion-card { border-left: 4px solid var(--color-accent); }
.card-header-iconic { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.suggestion-title { font-size: 0.9rem; font-weight: 800; color: #60a5fa; margin: 0; display: flex; align-items: center; gap: 8px; }
.action-buttons { display: flex; gap: 8px; }

.ai-content-box { min-height: 80px; display: flex; align-items: center; }
.ai-text { font-size: 1.05rem; color: var(--text-primary); line-height: 1.8; margin: 0; font-weight: 500; }
.ai-text-placeholder { color: var(--text-tertiary); font-style: italic; font-size: 0.95rem; }

/* Skeleton Loader */
.skeleton-loader {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg,
    var(--color-bg-base) 0%,
    rgba(255, 255, 255, 0.1) 50%,
    var(--color-bg-base) 100%);
  background-size: 200% 100%;
  border-radius: 8px;
  animation: skeleton-shimmer 1.5s infinite;
}

.skeleton-line.short { width: 60%; }
.skeleton-line.medium { width: 80%; }

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

html.dark .skeleton-line {
  background: linear-gradient(90deg,
    rgba(255, 255, 255, 0.05) 0%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 255, 255, 0.05) 100%);
  background-size: 200% 100%;
}

.dual-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.col-title { font-size: 1.1rem; font-weight: 800; margin: 0 0 20px 0; display: flex; align-items: center; gap: 10px; }
.modern-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: var(--color-bg-base); border-radius: 16px; margin-bottom: 12px; transition: all 0.2s; }
.modern-item.clickable { cursor: pointer; }
.modern-item:hover { transform: scale(1.02); }
.modern-item.clickable:hover { transform: scale(1.05); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); border: 1px solid var(--color-accent); }
.item-main { display: flex; flex-direction: column; gap: 4px; }
.item-main .name { font-weight: 700; color: var(--text-primary); }
.item-main .meta, .item-main .reason { font-size: 0.75rem; color: var(--text-tertiary); }
.modern-item .price { font-weight: 800; color: var(--text-primary); font-family: 'JetBrains Mono'; }
.prob-badge { background: var(--color-accent); color: white; padding: 4px 10px; border-radius: 8px; font-weight: 800; font-size: 0.8rem; }

.num-font { font-family: 'JetBrains Mono', monospace; }
.hidden-audio { display: none; }
</style>
