<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getHealth } from '../api'

// --- 1. 类型定义 ---
type StatusLevel = 'healthy' | 'degraded' | 'down'

interface ServiceNode {
  id: string
  name: string
  status: StatusLevel
  latency?: number // ms
}

// --- 2. 状态聚合逻辑 (纯函数) ---
const calcOverallStatus = (services: ServiceNode[]): StatusLevel => {
  const core = services.find(s => s.id === 'core')

  // Rule 1: Core API is the red line
  if (!core || core.status === 'down') {
    return 'down'
  }
  if (core.status === 'degraded') {
    return 'degraded'
  }

  // Filter out core to check sub-services
  const subServices = services.filter(s => s.id !== 'core')
  if (subServices.length === 0) return core.status

  // Rule 2: Core is healthy/degraded
  const allHealthy = subServices.every(s => s.status === 'healthy')
  const allDown = subServices.length > 0 && subServices.every(s => s.status === 'down')

  if (allHealthy) return 'healthy'
  if (allDown) return 'down'

  // Partial availability
  return 'degraded'
}

// --- 3. 模拟数据与逻辑 ---
const loading = ref(false)
const services = ref<ServiceNode[]>([])
let statusTimer: number | undefined

const fetchStatus = async () => {
  loading.value = true
  const startedAt = performance.now()
  try {
    const health = await getHealth()
    const latency = Math.round(performance.now() - startedAt)
    services.value = [
      {
        id: 'core',
        name: health.service || 'Core API',
        status: health.status === 'healthy' ? 'healthy' : 'degraded',
        latency
      }
    ]
  } catch {
    services.value = [
      { id: 'core', name: 'Core API', status: 'down' }
    ]
  } finally {
    loading.value = false
  }
}

// 计算属性
const overallStatus = computed(() => calcOverallStatus(services.value))

const statusConfig = computed(() => {
  const map: Record<StatusLevel, { label: string, color: string }> = {
    healthy: { label: '系统正常', color: '#10B981' },
    degraded: { label: '部分异常', color: '#F59E0B' },
    down: { label: '服务离线', color: '#EF4444' }
  }
  return map[overallStatus.value] || map.down
})

const getStatusLabel = (s: StatusLevel) => {
  const map = { healthy: '正常', degraded: '延迟', down: '不可用' }
  return map[s]
}

onMounted(() => {
  fetchStatus()
  statusTimer = window.setInterval(fetchStatus, 30000)
})

onUnmounted(() => {
  if (statusTimer !== undefined) {
    window.clearInterval(statusTimer)
    statusTimer = undefined
  }
})
</script>

<template>
  <el-popover
    trigger="hover"
    placement="bottom"
    :width="260"
    popper-class="status-popover-glass"
    :show-arrow="false"
    transition="el-zoom-in-top"
  >
    <template #reference>
      <div class="status-pill-trigger" :class="overallStatus">
        <span class="status-dot-pulse"></span>
        <span class="status-text">{{ statusConfig.label }}</span>
      </div>
    </template>

    <!-- Detail Content -->
    <div class="status-detail-container">
      <div class="detail-header">
        <span class="header-title">服务状态详情</span>
        <span class="header-refresh" @click="fetchStatus" :class="{ spinning: loading }">↻</span>
      </div>

      <div class="divider"></div>

      <div class="service-list">
        <div v-for="s in services" :key="s.id" class="service-item">
          <div class="service-info">
            <span class="s-name">{{ s.name }}</span>
            <span v-if="s.latency" class="s-latency">{{ s.latency }}ms</span>
          </div>
          <div class="s-status" :class="s.status">
            <span class="s-dot"></span>
            {{ getStatusLabel(s.status) }}
          </div>
        </div>
      </div>
    </div>
  </el-popover>
</template>

<style scoped>
/* Trigger Pill Styling */
.status-pill-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--nav-pill-bg);
  border-radius: var(--radius-pill);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
}

.status-pill-trigger:hover {
  background: var(--nav-pill-hover);
  color: var(--text-primary);
}

.status-dot-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-pill-trigger.healthy .status-dot-pulse { background: #10B981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.4); }
.status-pill-trigger.degraded .status-dot-pulse { background: #F59E0B; }
.status-pill-trigger.down .status-dot-pulse { background: #EF4444; }

/* Detail Content Styling */
.status-detail-container {
  padding: 4px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  font-size: 0.8rem;
  color: var(--text-tertiary);
  font-weight: 600;
}

.header-refresh {
  cursor: pointer;
  font-size: 1rem;
  transition: color 0.2s;
}
.header-refresh:hover { color: var(--text-primary); }
.header-refresh.spinning { animation: spin 1s linear infinite; }

.divider {
  height: 1px;
  background: var(--border-subtle);
  margin-bottom: 12px;
}

.service-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.service-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.service-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.s-name {
  color: var(--text-primary);
  font-weight: 500;
}

.s-latency {
  font-size: 0.7rem;
  color: var(--text-tertiary);
  font-family: monospace;
}

.s-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.s-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.s-status.healthy { color: #10B981; }
.s-status.healthy .s-dot { background: #10B981; }

.s-status.degraded { color: #F59E0B; }
.s-status.degraded .s-dot { background: #F59E0B; }

.s-status.down { color: #EF4444; }
.s-status.down .s-dot { background: #EF4444; }

@keyframes spin { 100% { transform: rotate(360deg); } }
</style>

<style>
/* Global Popover Override for Glassmorphism */
.el-popper.status-popover-glass {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(16px) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 16px !important;
  box-shadow: var(--shadow-lg) !important;
  padding: 16px !important;
}

html.dark .el-popper.status-popover-glass {
  background: rgba(30, 30, 32, 0.85) !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
}
</style>
