<script setup lang="ts">
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

type Mode = 'user' | 'product'

interface RecommendItem {
  items?: string[]
  support?: number
  confidence?: number
  lift?: number
  reason?: string
  from_items?: string[]
  customers?: string[]
}

interface TargetCustomer {
  cluster_id?: number
  cluster_name?: string
  user_id?: string
  recency?: number
  frequency?: number
  monetary?: number
  aov?: number
  from_items?: string[]
  support?: number
  confidence?: number
  lift?: number
  customers?: string[]
}

interface RecommendResponse {
  item: string
  recommends: RecommendItem[]
  target_customers: TargetCustomer[]
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

const placeholder = computed(() =>
  mode.value === 'user' ? '请输入用户ID，例如：U1001' : '请输入商品名称，例如：椅子'
)

const hasRules = computed(() => (data.value?.recommends?.length || 0) > 0)
const hasTargets = computed(() => (data.value?.target_customers?.length || 0) > 0)
const speechText = computed(() => data.value?.speech || '')

const formatPercent = (v?: number) =>
  typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '-'
const formatLift = (v?: number) => (typeof v === 'number' ? v.toFixed(2) : '-')

const search = async () => {
  if (!keyword.value.trim()) {
    ElMessage.warning(mode.value === 'user' ? '请输入用户ID' : '请输入商品名称')
    return
  }
  loading.value = true
  audioUrl.value = ''
  try {
    const url = mode.value === 'user' ? '/api/recommend/user' : '/api/recommend/product'
    const params =
      mode.value === 'user'
        ? { user_id: keyword.value.trim() }
        : { item: keyword.value.trim() }
    const res = await axios.get(url, { params })
    data.value = res.data
    if (!hasRules.value) {
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
    const res = await axios.post('/api/recommend/tts/play', { speech: speechText.value })
    const url = res.data?.audio_url
    if (url) {
      audioUrl.value = url
      // 自动播放
      const audio = new Audio(url)
      audio.play().catch(() => {
        // 静默失败
      })
    }
  } catch (e) {
    ElMessage.error('语音生成失败')
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
        <span class="page-title">🎯 商品推荐 / 用户匹配</span>
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
                :type="mode === 'product' ? 'primary' : 'default'"
                @click="switchMode('product')"
              >
                按商品逆向
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
          <el-table :data="data?.recommends" stripe style="min-width: 720px;">
            <el-table-column label="推荐商品" min-width="160">
              <template #default="{ row }">
                <el-tag
                  v-for="(it, idx) in row.items || row.to_items"
                  :key="idx"
                  size="small"
                  type="info"
                  class="tag"
                >
                  {{ it }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="support" label="支持度" width="100">
              <template #default="{ row }">{{ formatPercent(row.support) }}</template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="100">
              <template #default="{ row }">{{ formatPercent(row.confidence) }}</template>
            </el-table-column>
            <el-table-column prop="lift" label="提升度" width="90">
              <template #default="{ row }">{{ formatLift(row.lift) }}</template>
            </el-table-column>
            <el-table-column label="推荐理由" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ row.reason || row.strategy || '-' }}</template>
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
          <el-table :data="data?.target_customers" stripe style="min-width: 720px;">
            <el-table-column label="群体 / 客户" min-width="180">
              <template #default="{ row }">
                <div v-if="row.cluster_name">
                  <el-tag type="success" size="small" class="tag">{{ row.cluster_name }}</el-tag>
                  <span class="muted">ID: {{ row.cluster_id ?? '-' }}</span>
                </div>
                <div v-else-if="row.customers">
                  <el-tag type="success" size="small" class="tag">目标客户</el-tag>
                  <div class="tag-wrap">
                    <el-tag
                      v-for="(c, idx) in row.customers"
                      :key="idx"
                      type="success"
                      size="small"
                      class="tag"
                    >
                      {{ c }}
                    </el-tag>
                  </div>
                </div>
                <div v-else>-</div>
              </template>
            </el-table-column>

            <el-table-column v-if="mode === 'product'" label="前项组合" min-width="160">
              <template #default="{ row }">
                <el-tag
                  v-for="(it, idx) in row.from_items || []"
                  :key="idx"
                  size="small"
                  type="info"
                  class="tag"
                >
                  {{ it }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="support" label="支持度" width="100">
              <template #default="{ row }">{{ formatPercent(row.support) }}</template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="100">
              <template #default="{ row }">{{ formatPercent(row.confidence) }}</template>
            </el-table-column>
            <el-table-column prop="lift" label="提升度" width="90">
              <template #default="{ row }">{{ formatLift(row.lift) }}</template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="暂无目标顾客对象" />
      </el-card>

      <!-- 播报 -->
      <div class="tts-bar" v-if="speechText">
        <div class="speech-text">播报内容：{{ speechText }}</div>
        <div class="tts-actions">
          <el-button type="primary" :loading="ttsLoading" @click="playTTS">🔊 播放播报</el-button>
          <audio v-if="audioUrl" :src="audioUrl" controls style="max-width: 320px; width: 100%;" />
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

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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
