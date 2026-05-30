<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getEventLogs, getAuditLogs, getExportUrl, type AdminLogPage } from '@/api/admin'
import { FileJson, FileSpreadsheet } from 'lucide-vue-next'

const activeTab = ref<'events' | 'audit'>('events')
const loading = ref(true)
const error = ref<string | null>(null)
const page = ref<AdminLogPage | null>(null)

const filterLevel = ref('')
const filterEventType = ref('')
const filterActorId = ref('')
const currentPage = ref(0)
const limit = 20

async function fetchLogs() {
  loading.value = true; error.value = null
  try {
    const params: any = { offset: currentPage.value * limit, limit }
    if (filterLevel.value) params.level = filterLevel.value
    if (filterEventType.value) params.eventType = filterEventType.value
    if (filterActorId.value) params.actorUserId = filterActorId.value
    page.value = activeTab.value === 'events'
      ? await getEventLogs(params)
      : await getAuditLogs(params)
  } catch (e: any) {
    error.value = e?.message || '获取日志失败'
  } finally { loading.value = false }
}

function exportUrl(format: 'json' | 'csv'): string {
  const params: Record<string, string> = {}
  if (filterLevel.value) params.level = filterLevel.value
  if (filterEventType.value) params.eventType = filterEventType.value
  if (filterActorId.value) params.actorUserId = filterActorId.value
  return getExportUrl(activeTab.value, format, params)
}

const levelColors: Record<string, string> = {
  info: '#3B82F6', warning: '#F59E0B', error: '#EF4444', critical: '#7C3AED',
}

function switchTab(tab: 'events' | 'audit') {
  activeTab.value = tab; currentPage.value = 0; fetchLogs()
}

onMounted(fetchLogs)
</script>

<template>
  <div class="logs-view">
    <header class="page-header">
      <div>
        <h1 class="page-title">系统日志</h1>
        <p class="page-sub">查看事件日志与审计记录，支持筛选与导出</p>
      </div>
    </header>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'events' }" @click="switchTab('events')">事件日志</button>
      <button class="tab" :class="{ active: activeTab === 'audit' }" @click="switchTab('audit')">审计日志</button>
    </div>

    <!-- Filters -->
    <div class="filters">
      <select v-model="filterLevel" class="filter-select" @change="currentPage=0;fetchLogs()">
        <option value="">全部级别</option>
        <option value="info">Info</option>
        <option value="warning">Warning</option>
        <option value="error">Error</option>
        <option value="critical">Critical</option>
      </select>
      <input v-model="filterEventType" placeholder="事件类型..." class="filter-input" @change="currentPage=0;fetchLogs()" />
      <input v-model="filterActorId" placeholder="操作人 ID..." class="filter-input" @change="currentPage=0;fetchLogs()" />
      <div class="export-btns">
        <a :href="exportUrl('json')" class="export-btn"><FileJson class="w-3.5 h-3.5" />JSON</a>
        <a :href="exportUrl('csv')" class="export-btn"><FileSpreadsheet class="w-3.5 h-3.5" />CSV</a>
      </div>
    </div>

    <div v-if="loading" class="loading-state"><div class="spinner"></div></div>
    <div v-else-if="error" class="error-state">{{ error }}</div>

    <!-- Table -->
    <div v-else-if="page" class="table-wrap">
      <table class="log-table">
        <thead>
          <tr><th>时间</th><th>级别</th><th>类型</th><th>消息</th><th>操作人</th></tr>
        </thead>
        <tbody>
          <tr v-if="page.items.length === 0"><td colspan="5" class="empty-row">暂无日志记录</td></tr>
          <tr v-for="item in page.items" :key="item.id">
            <td class="cell-time">{{ item.createdAt ? new Date(item.createdAt).toLocaleString() : '-' }}</td>
            <td><span class="level-badge" :style="{ background: levelColors[item.level]+'15', color: levelColors[item.level] }">{{ item.level }}</span></td>
            <td class="cell-type">{{ item.eventType }}</td>
            <td class="cell-msg">{{ item.message }}</td>
            <td class="cell-actor">{{ item.actorUserId || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <button :disabled="currentPage===0" @click="currentPage--;fetchLogs()">上一页</button>
        <span>{{ currentPage+1 }} / {{ Math.ceil((page.total||1)/limit) }}</span>
        <button :disabled="(currentPage+1)*limit >= page.total" @click="currentPage++;fetchLogs()">下一页</button>
        <span class="total">共 {{ page.total }} 条</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: 28px; }
.page-title { font-size: 1.75rem; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0; letter-spacing: -0.02em; }
.page-sub { font-size: 0.9rem; color: var(--text-tertiary); margin: 0; }

/* ─── tabs ─── */
.tabs { display: flex; gap: 4px; margin-bottom: 18px; }
.tab {
  padding: 9px 20px; border-radius: 14px; border: none;
  font-size: 0.85rem; font-weight: 500; color: var(--text-secondary);
  background: transparent; cursor: pointer; transition: all 0.2s ease;
}
.tab:hover { color: var(--text-primary); background: var(--color-surface-hover); }
.tab.active { color: #6366F1; background: rgba(99,102,241,0.08); font-weight: 600; }

/* ─── filters ─── */
.filters { display: flex; gap: 10px; align-items: center; margin-bottom: 18px; flex-wrap: wrap; }
.filter-select, .filter-input {
  height: 40px; padding: 0 14px; border-radius: 14px; font-size: 0.82rem;
  background: var(--color-surface); border: 1px solid var(--border-subtle);
  color: var(--text-primary); outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.filter-select:focus, .filter-input:focus { border-color: rgba(99,102,241,0.35); box-shadow: 0 0 0 3px rgba(99,102,241,0.06); }
.export-btns { display: flex; gap: 6px; margin-left: auto; }
.export-btn {
  display: inline-flex; align-items: center; gap: 4px; padding: 8px 14px;
  border-radius: 14px; background: rgba(99,102,241,0.06); color: #6366F1;
  font-size: 0.82rem; font-weight: 500; text-decoration: none; transition: background 0.15s;
}
.export-btn:hover { background: rgba(99,102,241,0.12); }

/* ─── table ─── */
.table-wrap {
  background: var(--color-surface); border: 1px solid var(--border-subtle);
  border-radius: 20px; overflow: hidden;
  box-shadow: var(--shadow-xs);
}
.log-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.log-table th {
  text-align: left; padding: 14px 18px; font-size: 0.72rem; font-weight: 600;
  color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--color-surface-hover);
}
.log-table td { padding: 11px 18px; color: var(--text-secondary); border-bottom: 1px solid var(--border-subtle); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--color-surface-hover); }
.empty-row { text-align: center; color: var(--text-tertiary); padding: 32px 18px !important; }

.level-badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
.cell-time { white-space: nowrap; font-size: 0.8rem; color: var(--text-tertiary); }
.cell-type { font-weight: 500; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-msg { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cell-actor { font-family: 'SF Mono', monospace; font-size: 0.78rem; color: var(--text-tertiary); }

/* ─── pagination ─── */
.pagination { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 14px; border-top: 1px solid var(--border-subtle); }
.pagination button {
  padding: 6px 14px; border-radius: 10px; border: 1px solid var(--border-subtle);
  background: var(--color-surface); color: var(--text-secondary); font-size: 0.82rem; cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.pagination button:hover:not(:disabled) { border-color: rgba(99,102,241,0.3); color: #6366F1; }
.pagination button:disabled { opacity: 0.35; cursor: not-allowed; }
.pagination span { font-size: 0.82rem; color: var(--text-secondary); }
.total { color: var(--text-tertiary) !important; }

.loading-state { display: flex; justify-content: center; padding: 60px 0; }
.spinner { width: 36px; height: 36px; border: 3px solid var(--border-subtle); border-radius: 50%; border-top-color: #6366F1; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-state { text-align: center; padding: 60px 0; color: #EF4444; font-size: 0.9rem; }
</style>
