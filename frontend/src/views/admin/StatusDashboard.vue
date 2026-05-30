<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { getAdminStatusSummary, type AdminStatusSummary } from '@/api/admin'
import { CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-vue-next'

const summary = ref<AdminStatusSummary | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

const overallConfig = computed(() => {
  const s = summary.value?.overallStatus
  const map: Record<string, { color: string; label: string }> = {
    healthy: { color: '#10B981', label: '系统正常' },
    degraded: { color: '#F59E0B', label: '部分降级' },
    down: { color: '#EF4444', label: '服务宕机' },
    unknown: { color: '#9CA3AF', label: '状态未知' },
  }
  return map[s || 'unknown'] || map.unknown
})

function statusIcon(status: string) {
  switch (status) {
    case 'healthy': return CheckCircle
    case 'degraded': return AlertTriangle
    case 'down': return XCircle
    default: return HelpCircle
  }
}

function statusColor(status: string): string {
  switch (status) {
    case 'healthy': return '#10B981'
    case 'degraded': return '#F59E0B'
    case 'down': return '#EF4444'
    default: return '#9CA3AF'
  }
}

function categoryLabel(cat: string): string {
  const map: Record<string, string> = { app: '应用', infra: '基础设施', external: '外部服务' }
  return map[cat] || cat
}

async function fetchStatus() {
  try {
    summary.value = await getAdminStatusSummary()
    error.value = null
  } catch (e: any) {
    error.value = e?.message || '获取状态失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
  timer = setInterval(fetchStatus, 30_000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="status-dashboard">
    <h1 class="page-title">运行状态看板</h1>

    <!-- Overall Banner -->
    <div v-if="summary" class="overall-banner" :style="{ borderColor: overallConfig.color }">
      <div class="banner-dot" :style="{ background: overallConfig.color }"></div>
      <span class="banner-text">{{ overallConfig.label }}</span>
      <span class="banner-time">{{ summary.generatedAt ? new Date(summary.generatedAt).toLocaleTimeString() : '' }}</span>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <!-- Service Cards Grid by category -->
    <template v-if="summary">
      <div v-for="cat in ['app', 'infra', 'external']" :key="cat" class="category-section">
        <h2 class="category-title">{{ categoryLabel(cat) }}</h2>
        <div class="cards-grid">
          <div
            v-for="svc in summary.services.filter(s => s.category === cat)"
            :key="svc.key"
            class="service-card"
            :style="{ borderColor: statusColor(svc.status) + '40' }"
          >
            <div class="card-header">
              <component :is="statusIcon(svc.status)" :size="20" :color="statusColor(svc.status)" />
              <span class="card-name">{{ svc.name }}</span>
              <span class="card-status" :style="{ color: statusColor(svc.status) }">{{ svc.status }}</span>
            </div>
            <div class="card-body">
              <div v-if="svc.latencyMs != null" class="card-metric">
                <span class="metric-label">延迟</span>
                <span class="metric-value">{{ svc.latencyMs.toFixed(1) }}ms</span>
              </div>
              <div v-if="svc.version" class="card-metric">
                <span class="metric-label">版本</span>
                <span class="metric-value">{{ svc.version }}</span>
              </div>
            </div>
            <div v-if="svc.message" class="card-footer">
              <span class="card-message">{{ svc.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 24px;
}

html.dark .page-title { color: #f1f5f9; }

.overall-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  border-radius: 14px;
  background: #fff;
  border: 2px solid;
  margin-bottom: 28px;
}

html.dark .overall-banner { background: #1a1a20; }

.banner-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.banner-text {
  font-size: 1.1rem;
  font-weight: 600;
  color: #111827;
}

html.dark .banner-text { color: #f1f5f9; }

.banner-time {
  margin-left: auto;
  font-size: 0.8rem;
  color: #94a3b8;
}

.category-section { margin-bottom: 24px; }

.category-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 12px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.service-card {
  background: #fff;
  border: 1px solid;
  border-radius: 12px;
  padding: 16px;
  transition: box-shadow 160ms ease;
}

html.dark .service-card { background: #1a1a20; }

.service-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.card-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: #111827;
  flex: 1;
}

html.dark .card-name { color: #f1f5f9; }

.card-status {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.card-body {
  display: flex;
  gap: 16px;
}

.card-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-label {
  font-size: 0.7rem;
  color: #94a3b8;
  text-transform: uppercase;
}

.metric-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  font-family: monospace;
}

.card-footer { margin-top: 8px; }

.card-message {
  font-size: 0.78rem;
  color: #94a3b8;
}

.loading-state, .error-state {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 0.9rem;
}

.error-state { color: #EF4444; }
</style>
