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

const statusIcons: Record<string, typeof CheckCircle> = {
  healthy: CheckCircle,
  degraded: AlertTriangle,
  down: XCircle,
  unknown: HelpCircle,
}

const statusColors: Record<string, string> = {
  healthy: '#10B981',
  degraded: '#F59E0B',
  down: '#EF4444',
  unknown: '#9CA3AF',
}

const categoryLabels: Record<string, string> = {
  app: '应用服务',
  infra: '基础设施',
  external: '外部服务',
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
    <header class="page-header">
      <div>
        <h1 class="page-title">运行状态看板</h1>
        <p class="page-sub">实时监控各服务的健康状态与延迟</p>
      </div>
    </header>

    <!-- Overall Banner -->
    <div v-if="summary" class="overall-banner" :style="{ borderColor: overallConfig.color }">
      <span class="banner-dot" :style="{ background: overallConfig.color }"></span>
      <span class="banner-text">{{ overallConfig.label }}</span>
      <span class="banner-time">{{ summary.generatedAt ? new Date(summary.generatedAt).toLocaleTimeString() : '' }}</span>
    </div>

    <div v-if="loading" class="loading-state"><div class="spinner"></div></div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <!-- Service Cards Grid -->
    <template v-if="summary">
      <div v-for="cat in ['app', 'infra', 'external']" :key="cat" class="category-section">
        <h2 class="category-title">{{ categoryLabels[cat] }}</h2>
        <div class="cards-grid">
          <div
            v-for="svc in summary.services.filter(s => s.category === cat)"
            :key="svc.key"
            class="service-card"
          >
            <div class="card-header">
              <component :is="statusIcons[svc.status] || HelpCircle" class="w-4 h-4" :color="statusColors[svc.status]" />
              <span class="card-name">{{ svc.name }}</span>
              <span class="card-status" :style="{ color: statusColors[svc.status] }">{{ svc.status }}</span>
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
              {{ svc.message }}
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: 32px; }
.page-title { font-size: 1.75rem; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0; letter-spacing: -0.02em; }
.page-sub { font-size: 0.9rem; color: var(--text-tertiary); margin: 0; }

/* ─── overall banner ─── */
.overall-banner {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 24px; border-radius: 20px; border: 2px solid;
  background: var(--color-surface);
  margin-bottom: 36px;
  box-shadow: var(--shadow-sm);
}
.banner-dot { width: 10px; height: 10px; border-radius: 50%; }
.banner-text { font-size: 1.05rem; font-weight: 700; color: var(--text-primary); }
.banner-time { margin-left: auto; font-size: 0.82rem; color: var(--text-tertiary); }

/* ─── category ─── */
.category-section { margin-bottom: 32px; }
.category-title {
  font-size: 0.8rem; font-weight: 600; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 14px;
}

/* ─── grid ─── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

/* ─── card ─── */
.service-card {
  background: var(--color-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  padding: 22px 24px;
  box-shadow: var(--shadow-xs);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.service-card:hover {
  transform: translateY(-1px);
  border-color: rgba(99, 102, 241, 0.18);
  box-shadow: var(--shadow-sm);
}

.card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.card-name { font-weight: 600; font-size: 0.92rem; color: var(--text-primary); flex: 1; }
.card-status {
  font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
  padding: 2px 8px; border-radius: 999px;
  background: rgba(148, 163, 184, 0.08);
}

.card-body { display: flex; gap: 20px; }
.card-metric { display: flex; flex-direction: column; gap: 2px; }
.metric-label { font-size: 0.7rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; }
.metric-value { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); font-family: 'SF Mono', monospace; }

.card-footer { margin-top: 10px; font-size: 0.78rem; color: var(--text-tertiary); }

/* ─── states ─── */
.loading-state { display: flex; justify-content: center; padding: 60px 0; }
.spinner { width: 36px; height: 36px; border: 3px solid var(--border-subtle); border-radius: 50%; border-top-color: #6366F1; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-state { text-align: center; padding: 60px 0; color: #EF4444; font-size: 0.9rem; }
</style>
