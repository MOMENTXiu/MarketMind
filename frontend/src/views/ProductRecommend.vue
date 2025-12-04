<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

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
  from_items?: string[]
}

interface RecommendResponse {
  item: string
  recommends?: RecommendItem[]
  target_customers?: TargetCustomer[]
  speech?: string
  model_tries?: number
  human_fallback?: boolean
}

const mode = ref<Mode>('user')
const keyword = ref('')
const loading = ref(false)
const ttsLoading = ref(false)
const audioUrl = ref('')
const data = ref<RecommendResponse | null>(null)
const audioRef = ref<HTMLAudioElement | null>(null)

const placeholder = computed(() =>
  mode.value === 'user' ? '请输入用户ID，例如：U1001' : '请输入商品名称，例如：椅子'
)

const hasRules = computed(() => (data.value?.recommends?.length || 0) > 0)
const hasTargets = computed(() => (data.value?.target_customers?.length || 0) > 0)
const speechText = computed(() => data.value?.speech || '')

const formatPercent = (v?: number) =>
  typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '-'
const formatFloat = (v?: number, digits = 2) =>
  typeof v === 'number' ? v.toFixed(digits) : '-'

const search = async () => {
  if (!keyword.value.trim()) {
    ElMessage.warning(mode.value === 'user' ? '请输入用户ID' : '请输入商品名称')
    return
  }
  loading.value = true
  audioUrl.value = ''
  try {
    const url = mode.value === 'user' ? '/api/recommend/user' : '/api/recommend/item'
    const params =
      mode.value === 'user'
        ? { user_id: keyword.value.trim() }
        : { item: keyword.value.trim() }
    const res = await axios.get(url, { params })
    data.value = res.data
    if (!hasRules.value && !hasTargets.value) {
      ElMessage.info('暂无关联规则')
    }
  } catch (e) {
    ElMessage.error('查询失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const playTTS = async () => {
  if (!speechText.value) {
    ElMessage.info('暂无可播报内容')
    return
  }
  ttsLoading.value = true
  try {
    const res = await axios.post('/api/recommend/tts/play', {
      speech: speechText.value,
      project_id: 'recommend'
    })
    const url = res.data?.audio_url
    if (url) {
      audioUrl.value = url
      // 自动播放
      requestAnimationFrame(() => {
        audioRef.value?.play().catch(() => {})
      })
    }
  } catch (e: any) {
    ElMessage.error(`语音生成失败：${e?.response?.data?.detail || e?.message || '请稍后重试'}`)
  } finally {
    ttsLoading.value = false
  }
}

const switchMode = (m: Mode) => {
  if (mode.value !== m) {
    mode.value = m
    keyword.value = ''
    data.value = null
    audioUrl.value = ''
  }
}
</script>

<template>
  <div class="page-container">
    <el-page-header @back="$router.push('/projects')" title="返回">
      <template #content>
        <span class="page-title">🎯 商品/用户推荐</span>
      </template>
    </el-page-header>

    <div class="content">
      <!-- 搜索栏 -->
      <el-card class="search-card">
        <div class="search-row">
          <div class="mode-toggle">
            <el-button-group>
              <el-button
                :type="mode === 'user' ? 'primary' : 'default'"
                @click="switchMode('user')"
              >
                按用户推荐
              </el-button>
              <el-button
                :type="mode === 'item' ? 'primary' : 'default'"
                @click="switchMode('item')"
              >
                按商品推荐
              </el-button>
            </el-button-group>
          </div>
          <div class="search-input">
            <el-input
              v-model="keyword"
              :placeholder="placeholder"
              clearable
              @keyup.enter="search"
            />
          </div>
          <el-button type="primary" :loading="loading" @click="search">查询</el-button>
        </div>
      </el-card>

      <!-- 关联推荐卡片 -->
      <el-card class="result-card">
        <template #header>
          <div class="card-header">
            <span>关联推荐</span>
            <span v-if="data?.item" class="muted">目标：{{ data.item }}</span>
          </div>
        </template>

        <div v-if="hasRules" class="table-wrapper">
          <el-table :data="data?.recommends" stripe style="min-width: 820px;">
            <el-table-column label="推荐商品" min-width="160">
              <template #default="{ row }">
                <el-tag type="success" size="small" class="tag">{{ row.item }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="所属类别" min-width="140">
              <template #default="{ row }">
                <el-tag type="info" size="small" class="tag">{{ row.category || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="推荐分" width="120">
              <template #default="{ row }">{{ formatFloat(row.score) }}</template>
            </el-table-column>
            <el-table-column label="推荐理由" min-width="240" show-overflow-tooltip>
              <template #default="{ row }">{{ row.reason || '-' }}</template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="暂无关联规则" />
      </el-card>

      <!-- 目标顾客对象卡片 -->
      <el-card class="result-card">
        <template #header>
          <div class="card-header">
            <span>目标顾客对象</span>
          </div>
        </template>

        <div v-if="hasTargets" class="table-wrapper">
          <el-table :data="data?.target_customers" stripe style="min-width: 820px;">
            <el-table-column label="群体" min-width="180">
              <template #default="{ row }">
                <el-tag type="success" size="small" class="tag">{{ row.cluster_name || '目标群体' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column v-if="mode === 'item'" label="后项" min-width="120">
              <template #default="{ row }">
                <el-tag
                  v-for="(it, idx) in row.to_items || [data?.item]"
                  :key="idx"
                  type="success"
                  size="small"
                  class="tag"
                >
                  {{ it }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column v-if="mode === 'item'" label="前项组合" min-width="160">
              <template #default="{ row }">
                <el-tag
                  v-for="(it, idx) in row.from_items || []"
                  :key="idx"
                  type="info"
                  size="small"
                  class="tag"
                >
                  {{ it }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="购买倾向/提升" width="140">
              <template #default="{ row }">
                <span>{{ formatFloat(row.lift_index || row.buy_ratio) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="策略" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ row.strategy || '-' }}</template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="暂无关联规则" />
      </el-card>

      <!-- 播报 -->
      <div class="tts-bar" v-if="speechText">
        <div class="speech-text">播报内容：{{ speechText }}</div>
        <div class="tts-actions">
          <el-button type="primary" :loading="ttsLoading" @click="playTTS">🔊 播放播报</el-button>
          <audio v-if="audioUrl" ref="audioRef" :src="audioUrl" controls autoplay style="max-width: 320px; width: 100%;" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.search-card {
  padding-bottom: 0.5rem;
}

.search-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
}

.mode-toggle {
  display: flex;
}

.search-input {
  flex: 1;
  min-width: 240px;
}

.result-card {
  overflow-x: auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}

.muted {
  color: #94a3b8;
  font-size: 0.95rem;
}

.tag {
  margin-right: 6px;
  margin-bottom: 4px;
}

.table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.tts-bar {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: var(--surface, #ffffff);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.tts-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.speech-text {
  color: #475569;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .page-container {
    padding: 1rem;
  }
  .tts-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
