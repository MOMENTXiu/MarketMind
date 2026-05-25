<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import http from '@/utils/http'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Search, ArrowLeft, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'

const route = useRoute()

interface RelationNode {
  item: string
  confidence: number
  lift: number
}

interface RecommendResponse {
  item: string
  upstream: RelationNode[]
  downstream: RelationNode[]
  target_customers: any[]
  success: boolean
}

const keyword = ref('')
const loading = ref(false)
const data = ref<RecommendResponse | null>(null)
const insightText = ref('')
const displayedText = ref('')
const insightLoading = ref(false)
const typewriterActive = ref(false)
const voiceLoading = ref(false)
const audioRef = ref<HTMLAudioElement | null>(null)
const audioUrl = ref('')

// UI Refs for SVG drawing
const centerNodeRef = ref<HTMLElement | null>(null)
const sourceRefs = ref<HTMLElement[]>([])
const targetRefs = ref<HTMLElement[]>([])
const svgPathData = ref<{d: string, width: number}[]>([])

const startTypewriter = (text: string) => {
  typewriterActive.value = true
  displayedText.value = ''
  let i = 0
  const speed = 30 // ms per char
  
  const type = () => {
    if (i < text.length) {
      displayedText.value += text.charAt(i)
      i++
      setTimeout(type, speed)
    } else {
      typewriterActive.value = false
    }
  }
  type()
}

const search = async (targetItem?: string) => {
  const query = targetItem || keyword.value.trim()
  if (!query) return
  
  keyword.value = query
  loading.value = true
  data.value = null
  svgPathData.value = []
  sourceRefs.value = []
  targetRefs.value = []
  insightText.value = ''
  displayedText.value = ''
  
  try {
    const { data: res } = await http.get('/api/recommend/item/', { params: { item: query } })
    data.value = res

    // Trigger LLM insight
    generateLLMInsight()
    
    // Wait for DOM to render then draw lines
    setTimeout(() => {
      updateLines()
    }, 300)
  } catch (e: any) {
    console.error('Search error:', e)
    const msg = e.response?.data?.detail || e.message || '未知错误'
    ElMessage.error(`获取数据失败: ${msg}`)
  } finally {
    loading.value = false
  }
}

const generateLLMInsight = async () => {
  if (!data.value) return
  insightLoading.value = true
  insightText.value = ''
  displayedText.value = ''
  
  try {
    const savedLLM = localStorage.getItem('llm_config')
    if (!savedLLM) return
    const llmConfig = JSON.parse(savedLLM)
    
    const prompt = `你是一位商业顾问。请分析以下商品的双向关联数据，生成一段专业、客观、富有建议的简评（80字以内）。直接输出结论，严禁废话。
数据: ${JSON.stringify({ item: data.value.item, upstream: data.value.upstream, downstream: data.value.downstream })}`
    
    const res = await axios.post(`${llmConfig.baseUrl}/chat/completions`, {
      model: llmConfig.modelName,
      messages: [{ role: 'user', content: prompt }]
    }, { headers: { 'Authorization': `Bearer ${llmConfig.apiKey}` } })
    
    insightText.value = res.data.choices[0].message.content.trim()
    startTypewriter(insightText.value)
  } catch (e) {
    console.error('LLM error', e)
  } finally {
    insightLoading.value = false
  }
}

const playInsightVoice = async () => {
  if (!insightText.value) return
  voiceLoading.value = true
  try {
    const savedTTS = JSON.parse(localStorage.getItem('tts_config') || '{}')
    const { data: ttsData } = await http.post('/api/voice/tts/', {
      text: insightText.value,
      voice: savedTTS.voice || 'zh-CN-YunxiNeural',
      rate: savedTTS.rate || '+0%',
      volume: savedTTS.volume || '+0%'
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

const updateLines = () => {
  if (!centerNodeRef.value || !data.value) return
  
  const container = document.querySelector('.topology-container')
  if (!container) return
  const rect = container.getBoundingClientRect()
  const cRect = centerNodeRef.value.getBoundingClientRect()
  
  const cx = cRect.left - rect.left
  const cy = cRect.top - rect.top + cRect.height / 2
  const cw = cRect.width
  
  const paths: {d: string, width: number}[] = []
  
  // Upstream -> Center
  data.value.upstream.forEach((node, idx) => {
    const el = sourceRefs.value[idx]
    if (!el) return
    const r = el.getBoundingClientRect()
    const sx = r.left - rect.left + r.width
    const sy = r.top - rect.top + r.height / 2
    paths.push({
      d: createBezierPath(sx, sy, cx, cy),
      width: Math.max(1, node.confidence * 10)
    })
  })
  
  // Center -> Downstream
  data.value.downstream.forEach((node, idx) => {
    const el = targetRefs.value[idx]
    if (!el) return
    const r = el.getBoundingClientRect()
    const tx = r.left - rect.left
    const ty = r.top - rect.top + r.height / 2
    paths.push({
      d: createBezierPath(cx + cw, cy, tx, ty),
      width: Math.max(1, node.confidence * 10)
    })
  })
  
  svgPathData.value = paths
}

const createBezierPath = (x1: number, y1: number, x2: number, y2: number) => {
  const cp1x = x1 + (x2 - x1) / 2
  const cp2x = x1 + (x2 - x1) / 2
  return `M ${x1} ${y1} C ${cp1x} ${y1}, ${cp2x} ${y2}, ${x2} ${y2}`
}

// Handle window resize to redraw lines
onMounted(async () => {
  window.addEventListener('resize', updateLines)

  // Check query params
  const itemParam = route.query.item
  if (itemParam) {
    search(itemParam as string)
  }

  const customerId = route.query.customerId
  if (customerId) {
    try {
      const { data: customerRec } = await http.get('/api/recommend/user/', {
        params: { user_id: customerId }
      })
      if (customerRec.recommends && customerRec.recommends.length > 0) {
        const topItem = customerRec.recommends[0].item
        await search(topItem)
      }
    } catch (e) {
      console.error('Auto-load customer recommendation failed:', e)
    }
  }
})

const setSourceRef = (el: any) => { if (el) sourceRefs.value.push(el) }
const setTargetRef = (el: any) => { if (el) targetRefs.value.push(el) }

watch(data, () => {
  sourceRefs.value = []
  targetRefs.value = []
})
</script>

<template>
  <div class="recommend-center-layout">
    <div class="container-breath-fixed">
      <header class="page-navbar">
        <div class="nav-left">
          <el-button circle :icon="ArrowLeft" @click="$router.back()" class="btn-back" />
          <h1 class="text-display" style="font-size: 1.75rem;">商品关联思维导图</h1>
        </div>
        <div class="search-bar-inline">
          <el-input
            v-model="keyword"
            placeholder="搜索商品 (如: 椅子)"
            class="header-search"
            @keyup.enter="search()"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" :loading="loading" @click="search()">分析</el-button>
        </div>
      </header>

      <main class="topology-main">
        <div v-if="data || loading" class="topology-wrapper">
          <div class="topology-container">
            <!-- SVG Layer -->
            <svg class="topology-svg">
              <defs>
                <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" style="stop-color:var(--color-accent);stop-opacity:0.2" />
                  <stop offset="50%" style="stop-color:var(--color-accent);stop-opacity:0.6" />
                  <stop offset="100%" style="stop-color:var(--color-accent);stop-opacity:0.2" />
                </linearGradient>
              </defs>
              <path 
                v-for="(pathObj, idx) in svgPathData" 
                :key="idx" 
                :d="pathObj.d" 
                class="flow-line" 
                :style="{ strokeWidth: pathObj.width + 'px' }"
              />
            </svg>

            <!-- Column 1: Source -->
            <div class="topo-col side">
              <h4 class="col-label">关联来源</h4>
              <div class="node-list">
                <div 
                  v-for="node in data?.upstream || []" 
                  :key="node.item" 
                  class="topo-node source"
                  :ref="setSourceRef"
                  @click="search(node.item)"
                >
                  <span class="node-name">{{ node.item }}</span>
                  <span class="node-meta">置信度 {{ (node.confidence * 100).toFixed(0) }}%</span>
                </div>
                <div v-if="!data?.upstream.length && !loading" class="empty-node">无溯源规则</div>
              </div>
            </div>

            <!-- Column 2: Center -->
            <div class="topo-col center">
              <div class="center-glow-wrap">
                <div class="core-node" ref="centerNodeRef">
                  <el-icon class="core-icon" :class="{ 'is-loading': loading }">
                    <component :is="loading ? 'Loading' : 'Goods'" />
                  </el-icon>
                  <span class="core-name">{{ loading ? '分析中...' : data?.item }}</span>
                </div>
                <div class="breathing-ring" v-if="!loading"></div>
              </div>
            </div>

            <!-- Column 3: Target -->
            <div class="topo-col side">
              <h4 class="col-label">推荐去向</h4>
              <div class="node-list">
                <div 
                  v-for="node in data?.downstream || []" 
                  :key="node.item" 
                  class="topo-node target"
                  :ref="setTargetRef"
                  @click="search(node.item)"
                >
                  <span class="node-name">{{ node.item }}</span>
                  <span class="node-meta">推荐度 {{ (node.confidence * 100).toFixed(0) }}%</span>
                </div>
                <div v-if="!data?.downstream.length && !loading" class="empty-node">无推荐去向</div>
              </div>
            </div>
          </div>

          <!-- LLM Insight Section -->
          <section class="insight-section-glass">
            <div class="insight-header-floating">
              <div class="insight-title-group">
                <span>AI 商业洞察建议</span>
              </div>
              
              <el-button 
                v-if="insightText && !typewriterActive"
                round 
                size="small"
                @click="playInsightVoice"
                :loading="voiceLoading"
                class="btn-voice-glass"
              >
                <el-icon style="margin-right: 4px"><VideoPlay /></el-icon> 语音播报
              </el-button>
            </div>
            
            <div class="insight-text-flow">
              <p v-if="displayedText">{{ displayedText }}</p>
              <div v-else-if="insightLoading" class="skeleton-lines">
                <div class="skeleton-line" style="width: 100%"></div>
                <div class="skeleton-line" style="width: 90%"></div>
                <div class="skeleton-line" style="width: 60%"></div>
              </div>
            </div>
          </section>
        </div>

        <div v-else-if="!loading" class="empty-state-canvas">
          <el-icon class="huge-icon"><Refresh /></el-icon>
          <p>输入商品名称以开启双向关联分析</p>
        </div>
      </main>
    </div>
    <audio ref="audioRef" :src="audioUrl" class="hidden-audio"></audio>
  </div>
</template>

<style scoped>
.recommend-center-layout {
  min-height: 100vh;
  background: var(--color-bg-base);
  color: var(--text-primary);
  transition: background 0.5s ease;
}

.container-breath-fixed {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.page-navbar {
  height: 100px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 10;
  margin-bottom: 48px; /* mt-12 equivalent */
}

.search-bar-inline {
  display: flex;
  gap: 8px;
  width: auto;
  align-items: center;
}

.header-search {
  width: 240px !important;
}

:deep(.header-search .el-input__wrapper) {
  height: 40px !important;
  border-radius: 999px !important;
  background: var(--color-surface) !important;
  box-shadow: var(--shadow-sm) !important;
  border: 1px solid var(--border-subtle) !important;
  padding-left: 16px !important;
}

.search-bar-inline .el-button {
  height: 40px !important;
  border-radius: 999px !important;
  padding: 0 24px !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  background: var(--color-accent-soft) !important;
  border: 1px solid var(--color-accent) !important;
  color: var(--color-accent) !important;
  box-shadow: none;
  transition: all 0.3s ease;
}

html.dark .search-bar-inline .el-button {
  background: rgba(94, 106, 210, 0.1) !important;
  border-color: rgba(94, 106, 210, 0.3) !important;
}

.search-bar-inline .el-button:hover {
  background: var(--color-accent) !important;
  color: white !important;
  transform: translateY(-1px);
}

.topology-main {
  min-height: 600px;
  display: flex;
  flex-direction: column;
}

.topology-wrapper {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.topology-container {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1.2fr 1fr;
  gap: 40px;
  min-height: 450px;
  padding: 20px 0;
  overflow: visible; /* Ensure no clipping of shadows */
}

.topology-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.flow-line {
  fill: none;
  stroke: var(--color-accent);
  stroke-width: 2;
  stroke-opacity: 0.2;
  stroke-dasharray: 8, 4;
  animation: dash-move 20s linear infinite;
}

@keyframes dash-move {
  from { stroke-dashoffset: 100; }
  to { stroke-dashoffset: 0; }
}

.topo-col {
  display: flex;
  flex-direction: column;
  z-index: 1;
}

.topo-col.center {
  justify-content: center;
  align-items: center;
}

.col-label {
  text-align: center;
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 16px;
}

.node-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  justify-content: center;
  flex: 1;
}

.topo-node {
  background: var(--color-surface);
  padding: 12px 16px;
  border-radius: 16px;
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.3s var(--ease-spring);
  display: flex;
  flex-direction: column;
  gap: 2px;
  box-shadow: var(--shadow-sm);
}

.topo-node:hover {
  transform: scale(1.05) translateX(4px);
  border-color: var(--color-accent);
  box-shadow: var(--shadow-md);
}

.topo-node.source { border-left: 4px solid #A78BFA; }
.topo-node.target { border-left: 4px solid #22D3EE; }

.node-name { font-weight: 700; font-size: 0.95rem; color: var(--text-primary); }
.node-meta { font-size: 0.7rem; color: var(--text-tertiary); }

.center-glow-wrap {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}

.core-node {
  background: var(--color-accent);
  width: 180px;
  height: 180px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 8px;
  z-index: 2;
  box-shadow: 0 0 40px rgba(94, 106, 210, 0.3);
  text-align: center;
  padding: 16px;
}

.core-icon { font-size: 2rem; color: white; }
.core-name { font-weight: 850; font-size: 1.1rem; color: white; line-height: 1.2; }

.breathing-ring {
  position: absolute;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  border: 2px solid var(--color-accent);
  opacity: 0.3;
  animation: breathe 3s infinite ease-in-out;
}

@keyframes breathe {
  0%, 100% { transform: scale(1); opacity: 0.2; }
  50% { transform: scale(1.2); opacity: 0; }
}

/* Insight Section - Premium Frosted Card */
.insight-section-glass {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: 32px; /* Extra large rounded corners */
  padding: 32px 40px;
  margin-top: 40px;
  margin-bottom: 100px; /* Massive breathing room at bottom */
  position: relative;
  width: 840px; /* Fixed Width */
  height: 240px; /* Fixed Height */
  margin-left: auto;
  margin-right: auto;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.04);
  animation: fadeIn 0.8s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* Contain inner scroll */
}

html.dark .insight-section-glass {
  background: rgba(26, 26, 26, 0.75);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
}

.insight-header-floating {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-shrink: 0;
}

.insight-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 1.15rem;
  font-weight: 850;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.magic-icon {
  color: var(--color-accent);
  font-size: 1.4rem;
}

.insight-text-flow {
  flex: 1;
  overflow-y: auto; /* Handle long text gracefully */
  padding-right: 8px;
}

/* Custom scrollbar for premium feel */
.insight-text-flow::-webkit-scrollbar {
  width: 4px;
}
.insight-text-flow::-webkit-scrollbar-thumb {
  background: var(--border-subtle);
  border-radius: 10px;
}

.insight-text-flow p {
  font-size: 1.1rem;
  line-height: 1.8;
  color: var(--text-secondary);
  margin: 0;
  font-weight: 500;
  text-align: justify;
}

.placeholder-flow {
  color: var(--text-tertiary);
  font-style: italic;
}

/* Skeleton Loading - Enhanced to fill space */
.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
}

.skeleton-line {
  height: 18px;
  background: var(--nav-pill-bg);
  border-radius: 6px;
  animation: pulse 1.5s infinite ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 0.3; }
  100% { opacity: 0.6; }
}

.btn-voice-glass {
  background: var(--color-bg-base) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
  font-weight: 700 !important;
  padding: 8px 20px !important;
}

.btn-voice-glass:hover {
  background: var(--color-accent) !important;
  color: white !important;
}

.empty-state-canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 20px;
  opacity: 0.3;
  padding-top: 100px;
}

.huge-icon { font-size: 4rem; color: var(--text-tertiary); }

.btn-back {
  background: var(--color-surface) !important;
  border: 1px solid var(--border-subtle) !important;
  color: var(--text-primary) !important;
}

.hidden-audio { display: none; }
</style>