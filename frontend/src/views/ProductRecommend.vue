<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Search, User, Goods, VideoPause, ArrowLeft } from '@element-plus/icons-vue'

type Mode = 'user' | 'item'

interface RecommendItem {
  item?: string
  category?: string
  score?: number
  reason?: string
}

interface TargetCustomer {
  cluster_name?: string
  strategy?: string
  buyer_count?: number
  buy_ratio?: number
  lift_index?: number
  to_items?: string[]
}

interface RecommendResponse {
  item: string
  recommends?: RecommendItem[]
  target_customers?: TargetCustomer[]
  speech?: string
}

const mode = ref<Mode>('user')
const keyword = ref('')
const loading = ref(false)
const voiceLoading = ref(false)
const data = ref<RecommendResponse | null>(null)
const audioRef = ref<HTMLAudioElement | null>(null)
const audioUrl = ref('')
const subtitleText = ref('')
const showSubtitle = ref(false)

const placeholder = computed(() =>
  mode.value === 'user' ? '输入用户 ID (如: U1001)' : '输入商品子类别 (如: 椅子)'
)

const search = async () => {
  if (!keyword.value.trim()) return
  loading.value = true
  data.value = null
  try {
    const url = mode.value === 'user' ? '/api/recommend/user' : '/api/recommend/item'
    const params = mode.value === 'user' ? { user_id: keyword.value.trim() } : { item: keyword.value.trim() }
    const res = await axios.get(url, { params })
    data.value = res.data
  } catch (e: any) {
    ElMessage.error('查询失败: ' + (e.response?.data?.detail || '服务未响应'))
  } finally {
    loading.value = false
  }
}

const playVoice = async () => {
  if (!data.value?.speech) return
  voiceLoading.value = true
  try {
    const text = data.value.speech
    subtitleText.value = text
    const res = await axios.post('/api/voice/tts', { text })
    if (res.data.success) {
      audioUrl.value = res.data.audio_url
      setTimeout(() => {
        audioRef.value?.play()
        showSubtitle.value = true
      }, 100)
    }
  } catch (e) {
    ElMessage.error('语音合成失败')
  } finally {
    voiceLoading.value = false
  }
}

const stopVoice = () => {
  audioRef.value?.pause()
  showSubtitle.value = false
}
</script>

<template>
  <div class="recommend-center-layout">
    <div class="container-breath-fixed">
      <header class="page-navbar">
        <div class="nav-left">
          <el-button circle :icon="ArrowLeft" @click="$router.back()" class="btn-back" />
          <h1 class="text-display" style="font-size: 1.75rem;">智能推荐中心</h1>
        </div>
        <div class="mode-pills">
          <button :class="{ active: mode === 'user' }" @click="mode = 'user'">
            <el-icon><User /></el-icon> 找商品
          </button>
          <button :class="{ active: mode === 'item' }" @click="mode = 'item'">
            <el-icon><Goods /></el-icon> 找客群
          </button>
        </div>
      </header>

      <main class="recommend-main">
        <!-- Search Focused Card -->
        <section class="glass-search-focus">
          <div class="search-input-wrapper">
            <el-input
              v-model="keyword"
              :placeholder="placeholder"
              size="large"
              class="large-search-input"
              @keyup.enter="search"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" size="large" @click="search" :loading="loading" class="btn-search-go">智能检索</el-button>
          </div>
        </section>

        <!-- Result Section -->
        <transition name="fade-up">
          <div v-if="data" class="recommend-results-grid">
            <!-- Recommendations List -->
            <div class="result-block-card glass-card" v-if="data.recommends?.length">
              <div class="block-header">
                <h3>💡 关联建议</h3>
                <el-button link type="primary" @click="playVoice" :loading="voiceLoading">🔊 语音解读</el-button>
              </div>
              <div class="rec-list-modern">
                <div v-for="rec in data.recommends" :key="rec.item" class="rec-item-modern">
                  <div class="item-info">
                    <span class="item-name">{{ rec.item }}</span>
                    <span class="item-reason">{{ rec.reason }}</span>
                  </div>
                  <div class="item-score">{{ ((rec.score || 0) * 100).toFixed(0) }}%</div>
                </div>
              </div>
            </div>

            <!-- Target Clusters -->
            <div class="result-block-card glass-card" v-if="data.target_customers?.length">
              <div class="block-header">
                <h3>👥 目标客群</h3>
              </div>
              <div class="target-grid-modern">
                <div v-for="tgt in data.target_customers" :key="tgt.cluster_name" class="target-card-modern">
                  <span class="cluster-label">{{ tgt.cluster_name }}</span>
                  <div class="target-stats">
                    <div class="stat"><span>{{ tgt.buyer_count }}</span>人已购</div>
                    <div class="stat">提升 <span>{{ (tgt.lift_index || 0).toFixed(1) }}</span>x</div>
                  </div>
                  <p class="target-strat">{{ tgt.strategy }}</p>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="!loading && keyword" class="empty-results">
             <!-- Placeholder for no results -->
          </div>
        </transition>
      </main>
    </div>

    <!-- Subtitle Overlay -->
    <div class="voice-subtitle-overlay" v-if="showSubtitle" @click="stopVoice">
      <div class="subtitle-box">
        <span class="pulse-icon"></span>
        <p>{{ subtitleText }}</p>
        <el-icon><VideoPause /></el-icon>
      </div>
    </div>

    <audio ref="audioRef" :src="audioUrl" @ended="showSubtitle = false" class="hidden-audio"></audio>
  </div>
</template>

<style scoped>
.recommend-center-layout {
  min-height: 100vh;
  background: var(--color-bg-base);
  padding-bottom: 100px;
}

.container-breath-fixed {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 24px;
}

.page-navbar {
  height: 100px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
}

.nav-left {
  display: flex;
  gap: 20px;
  align-items: center;
}

.btn-back {
  background: white;
  border: 1px solid var(--border-subtle);
  transition: 0.3s;
}

.btn-back:hover { transform: translateX(-4px); }

.mode-pills {
  background: rgba(0,0,0,0.05);
  padding: 4px;
  border-radius: 16px;
  display: flex;
  gap: 4px;
}

.mode-pills button {
  border: none;
  background: transparent;
  padding: 8px 20px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-pills button.active {
  background: white;
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}

.glass-search-focus {
  background: white;
  border-radius: 32px;
  padding: 40px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.04);
  margin-bottom: 48px;
  border: 1px solid rgba(0,0,0,0.02);
}

.search-input-wrapper {
  display: flex;
  gap: 16px;
}

.large-search-input {
  flex: 1;
}

:deep(.large-search-input .el-input__wrapper) {
  height: 60px !important;
  border-radius: 16px !important;
  font-size: 1.1rem !important;
  background: #F8F9FA !important;
}

.btn-search-go {
  height: 60px !important;
  padding: 0 40px !important;
  border-radius: 16px !important;
  font-weight: 700 !important;
}

.recommend-results-grid {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.glass-card {
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 32px;
  box-shadow: var(--shadow-sm);
  border: 1px solid rgba(255,255,255,0.5);
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.block-header h3 { margin: 0; font-size: 1.25rem; font-weight: 800; }

.rec-list-modern {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rec-item-modern {
  background: white;
  padding: 16px 24px;
  border-radius: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: 0.3s;
}

.rec-item-modern:hover { transform: scale(1.01); box-shadow: var(--shadow-sm); }

.item-name { font-weight: 700; font-size: 1.1rem; color: var(--text-primary); }
.item-reason { font-size: 0.85rem; color: var(--text-tertiary); display: block; margin-top: 4px; }
.item-score { font-weight: 800; color: var(--color-accent); background: var(--color-accent-soft); padding: 4px 12px; border-radius: 10px; }

.target-grid-modern {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.target-card-modern {
  background: white;
  padding: 24px;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cluster-label { font-weight: 800; font-size: 1.1rem; }
.target-stats { display: flex; gap: 16px; font-size: 0.9rem; font-weight: 600; color: var(--text-secondary); }
.target-stats span { color: var(--color-accent); font-weight: 800; }
.target-strat { font-size: 0.85rem; color: var(--text-tertiary); line-height: 1.5; }

/* Subtitle */
.voice-subtitle-overlay {
  position: fixed;
  bottom: 40px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  z-index: 2000;
  pointer-events: none;
}

.subtitle-box {
  background: rgba(0,0,0,0.85);
  backdrop-filter: blur(12px);
  padding: 16px 32px;
  border-radius: 40px;
  display: flex;
  align-items: center;
  gap: 16px;
  color: white;
  pointer-events: auto;
  cursor: pointer;
  box-shadow: 0 20px 50px rgba(0,0,0,0.3);
  max-width: 80%;
}

.subtitle-box p { margin: 0; font-size: 1rem; font-weight: 500; }

.hidden-audio { display: none; }

.fade-up-enter-active { transition: all 0.5s ease; }
.fade-up-enter-from { opacity: 0; transform: translateY(30px); }
</style>