<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getEventLogs, getAuditLogs, getExportUrl, type AdminLogPage } from '@/api/admin'
import { FileJson, FileSpreadsheet } from 'lucide-vue-next'

const activeTab = ref<'events' | 'audit'>('events')
const loading = ref(true)
const error = ref<string | null>(null)
const page = ref<AdminLogPage | null>(null)

// Filters
const filterLevel = ref('')
const filterEventType = ref('')
const filterActorId = ref('')
const currentPage = ref(0)
const limit = 20

async function fetchLogs() {
  loading.value = true
  error.value = null
  try {
    const params: any = {
      offset: currentPage.value * limit,
      limit,
    }
    if (filterLevel.value) params.level = filterLevel.value
    if (filterEventType.value) params.eventType = filterEventType.value
    if (filterActorId.value) params.actorUserId = filterActorId.value

    if (activeTab.value === 'events') {
      page.value = await getEventLogs(params)
    } else {
      page.value = await getAuditLogs(params)
    }
  } catch (e: any) {
    error.value = e?.message || '获取日志失败'
  } finally {
    loading.value = false
  }
}

function exportUrl(format: 'json' | 'csv'): string {
  const params: Record<string, string> = {}
  if (filterLevel.value) params.level = filterLevel.value
  if (filterEventType.value) params.eventType = filterEventType.value
  if (filterActorId.value) params.actorUserId = filterActorId.value
  return getExportUrl(activeTab.value, format, params)
}

function levelColor(level: string): string {
  const map: Record<string, string> = {
    info: '#3B82F6',
    warning: '#F59E0B',
    error: '#EF4444',
    critical: '#7C3AED',
  }
  return map[level] || '#9CA3AF'
}

function switchTab(tab: 'events' | 'audit') {
  activeTab.value = tab
  currentPage.value = 0
  fetchLogs()
}

onMounted(fetchLogs)
</script>

<template>
  <div class="logs-view">
    <h1 class="page-title">系统日志</h1>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'events' }" @click="switchTab('events')">事件日志</button>
      <button class="tab" :class="{ active: activeTab === 'audit' }" @click="switchTab('audit')">审计日志</button>
    </div>

    <!-- Filters -->
    <div class="filters">
      <select v-model="filterLevel" class="filter-select" @change="currentPage = 0; fetchLogs()">
        <option value="">全部级别</option>
        <option value="info">Info</option>
        <option value="warning">Warning</option>
        <option value="error">Error</option>
        <option value="critical">Critical</option>
      </select>
      <input v-model="filterEventType" placeholder="事件类型..." class="filter-input" @change="currentPage = 0; fetchLogs()" />
      <input v-model="filterActorId" placeholder="操作人 ID..." class="filter-input" @change="currentPage = 0; fetchLogs()" />
      <div class="export-btns">
        <a :href="exportUrl('json')" class="export-btn" title="导出 JSON">
          <FileJson :size="14" /> JSON
        </a>
        <a :href="exportUrl('csv')" class="export-btn" title="导出 CSV">
          <FileSpreadsheet :size="14" /> CSV
        </a>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <!-- Table -->
    <div v-else-if="page" class="table-wrap">
      <table class="log-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>级别</th>
            <th>类型</th>
            <th>消息</th>
            <th>操作人</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="page.items.length === 0">
            <td colspan="5" class="empty-row">暂无日志记录</td>
          </tr>
          <tr v-for="item in page.items" :key="item.id">
            <td class="cell-time">{{ item.createdAt ? new Date(item.createdAt).toLocaleString() : '-' }}</td>
            <td>
              <span class="level-badge" :style="{ background: levelColor(item.level) + '20', color: levelColor(item.level) }">
                {{ item.level }}
              </span>
            </td>
            <td class="cell-type">{{ item.eventType }}</td>
            <td class="cell-msg">{{ item.message }}</td>
            <td class="cell-actor">{{ item.actorUserId || '-' }}</td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="pagination">
        <button :disabled="currentPage === 0" @click="currentPage--; fetchLogs()">上一页</button>
        <span>{{ currentPage + 1 }} / {{ Math.ceil((page.total || 1) / limit) }}</span>
        <button :disabled="(currentPage + 1) * limit >= page.total" @click="currentPage++; fetchLogs()">下一页</button>
        <span class="total">共 {{ page.total }} 条</span>
      </div>
    </div>
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

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  padding: 4px;
  background: rgba(15, 23, 42, 0.04);
  border-radius: 12px;
  width: fit-content;
}

html.dark .tabs { background: rgba(255, 255, 255, 0.04); }

.tab {
  padding: 8px 18px;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 500;
  color: #64748b;
  background: none;
  border: none;
  cursor: pointer;
  transition: all 160ms ease;
}

.tab:hover { color: #111827; }
html.dark .tab:hover { color: #f1f5f9; }

.tab.active {
  color: #4f46e5;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-weight: 600;
}

html.dark .tab.active { background: #2a2a30; color: #818cf8; }

.filters {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-select, .filter-input {
  padding: 7px 12px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  font-size: 0.82rem;
  background: #fff;
  color: #475569;
}

html.dark .filter-select, html.dark .filter-input {
  background: #1a1a20;
  border-color: rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
}

.export-btns {
  display: flex;
  gap: 6px;
  margin-left: auto;
}

.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  font-size: 0.8rem;
  font-weight: 500;
  text-decoration: none;
  transition: all 160ms ease;
}

.export-btn:hover { background: rgba(99, 102, 241, 0.2); }

.table-wrap {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
  overflow: hidden;
}

html.dark .table-wrap { background: #1a1a20; border-color: rgba(255, 255, 255, 0.06); }

.log-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.log-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.log-table td {
  padding: 10px 16px;
  color: #475569;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
}

html.dark .log-table td { color: #cbd5e1; }
html.dark .log-table td { border-color: rgba(255, 255, 255, 0.04); }

.empty-row { text-align: center; color: #94a3b8; }

.level-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 5px;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
}

.cell-time { white-space: nowrap; font-size: 0.8rem; color: #94a3b8; }
.cell-type { font-weight: 500; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-msg { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-actor { font-family: monospace; font-size: 0.78rem; }

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px;
}

.pagination button {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #fff;
  color: #475569;
  font-size: 0.82rem;
  cursor: pointer;
}

html.dark .pagination button { background: #1a1a20; border-color: rgba(255,255,255,0.08); color: #cbd5e1; }

.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }

.pagination span { font-size: 0.82rem; color: #64748b; }

.total { color: #94a3b8 !important; }

.loading-state, .error-state {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
}

.error-state { color: #EF4444; }
</style>
